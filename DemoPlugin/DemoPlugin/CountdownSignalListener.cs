namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Net;
    using System.Net.Sockets;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;

    internal static class CountdownSignalListener
    {
        private const Int32 UdpPort = 5005;
        private const Int32 MaxTimerId = 5;  // 5v5: 5 enemies

        private static readonly Object LockObject = new Object();

        private static UdpClient _udpClient;
        private static CancellationTokenSource _cts;
        private static Task _listenTask;

        public static void Start()
        {
            lock (LockObject)
            {
                if (_listenTask != null)
                {
                    return;
                }

                _cts = new CancellationTokenSource();
                _udpClient = new UdpClient(UdpPort);
                _listenTask = Task.Run(() => ListenLoop(_cts.Token));
                PluginLog.Info($"Countdown signal listener started on UDP port {UdpPort}");
            }
        }

        public static void Stop()
        {
            lock (LockObject)
            {
                if (_listenTask == null)
                {
                    return;
                }

                _cts.Cancel();
                _udpClient.Close();
                _cts.Dispose();
                _udpClient = null;
                _cts = null;
                _listenTask = null;
                PluginLog.Info("Countdown signal listener stopped");
            }
        }

        private static async Task ListenLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    var result = await _udpClient.ReceiveAsync();
                    var message = Encoding.UTF8.GetString(result.Buffer).Trim();

                    // Handle signal overlay messages (existing behavior)
                    SignalBlockState.HandleSignal(message);

                    // Handle CONFIG messages from the Python client
                    if (message.StartsWith("CONFIG:", StringComparison.OrdinalIgnoreCase))
                    {
                        HandleConfigMessage(message);
                        continue;
                    }

                    // Handle enemy alert messages (JSON broadcast from RPi)
                    if (message.StartsWith("CMD:ENEMY_ALERT:", StringComparison.OrdinalIgnoreCase))
                    {
                        HandleEnemyAlert(message);
                        continue;
                    }

                    // Handle countdown START signals (existing behavior)
                    var timerId = ParseTimerId(message);
                    if (timerId.HasValue)
                    {
                        CountdownState.StartCountdown(timerId.Value);
                        PluginLog.Info($"Countdown T{timerId.Value} started from UDP signal ({result.RemoteEndPoint})");
                    }
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    PluginLog.Warning(ex, "Countdown signal listener error");
                }
            }
        }

        /// <summary>
        /// Parse CONFIG messages:
        ///   CONFIG:ALLY1:JG        → assign role JG to ally slot 1
        ///   CONFIG:ENEMY3:安妮      → assign hero 安妮 to enemy slot 3
        ///   CONFIG:MY_ROLE:MID     → set own role
        /// </summary>
        private static void HandleConfigMessage(String message)
        {
            try
            {
                var parts = message.Split(new[] { ':' }, 3);
                if (parts.Length < 3)
                {
                    return;
                }

                var key = parts[1].Trim().ToUpperInvariant();
                var value = parts[2].Trim();

                if (key.StartsWith("ALLY") && key.Length > 4)
                {
                    if (Int32.TryParse(key.Substring(4), out var slot) && slot >= 1 && slot <= AllyChannelState.AllySlotCount)
                    {
                        AllyChannelState.SetAllyRole(slot, value);
                        PluginLog.Info($"Config: Ally slot {slot} = {value}");
                    }
                }
                else if (key.StartsWith("ENEMY") && key.Length > 5)
                {
                    if (Int32.TryParse(key.Substring(5), out var slot) && slot >= 1 && slot <= AllyChannelState.EnemySlotCount)
                    {
                        AllyChannelState.SetEnemyHero(slot, value);
                        PluginLog.Info($"Config: Enemy slot {slot} = {value}");
                    }
                }
                else if (key == "MY_ROLE")
                {
                    AllyChannelState.SetMyRole(value);
                    PluginLog.Info($"Config: My role = {value}");
                }
            }
            catch (Exception ex)
            {
                PluginLog.Warning(ex, "Failed to parse CONFIG message");
            }
        }

        /// <summary>
        /// Handle CMD:ENEMY_ALERT:{json} — parse the JSON to find the target hero,
        /// look up its timer ID, and trigger the countdown.
        /// </summary>
        private static void HandleEnemyAlert(String message)
        {
            try
            {
                // Extract JSON payload after "CMD:ENEMY_ALERT:"
                var jsonStr = message.Substring("CMD:ENEMY_ALERT:".Length).Trim();
                PluginLog.Info($"Enemy alert received: {jsonStr}");

                // Simple parsing: look for "target" or "which character" field
                // We do lightweight string search to avoid adding a JSON library dependency.
                var target = ExtractJsonField(jsonStr, "which character")
                          ?? ExtractJsonField(jsonStr, "target")
                          ?? "";

                if (String.IsNullOrEmpty(target))
                {
                    PluginLog.Warning("Enemy alert: no target found in JSON");
                    return;
                }

                // Find timer ID for this hero
                var timerId = FindTimerIdForHero(target);
                if (timerId.HasValue)
                {
                    CountdownState.StartCountdown(timerId.Value);
                    PluginLog.Info($"Enemy alert: started countdown T{timerId.Value} for {target}");
                }
                else
                {
                    PluginLog.Warning($"Enemy alert: no timer mapping for hero '{target}'");
                }
            }
            catch (Exception ex)
            {
                PluginLog.Warning(ex, "Failed to handle ENEMY_ALERT");
            }
        }

        /// <summary>Lightweight JSON field extraction (avoids Newtonsoft dependency).</summary>
        private static String ExtractJsonField(String json, String fieldName)
        {
            var searchKey = $"\"{fieldName}\"";
            var keyIndex = json.IndexOf(searchKey, StringComparison.OrdinalIgnoreCase);
            if (keyIndex < 0) return null;

            var colonIndex = json.IndexOf(':', keyIndex + searchKey.Length);
            if (colonIndex < 0) return null;

            var quoteStart = json.IndexOf('"', colonIndex + 1);
            if (quoteStart < 0) return null;

            var quoteEnd = json.IndexOf('"', quoteStart + 1);
            if (quoteEnd < 0) return null;

            return json.Substring(quoteStart + 1, quoteEnd - quoteStart - 1);
        }

        /// <summary>Look up hero name → timer ID (1-based). Check dynamic config first, then static map.</summary>
        private static Int32? FindTimerIdForHero(String heroName)
        {
            // Check dynamically configured enemy slots first
            for (var slot = 1; slot <= AllyChannelState.EnemySlotCount; slot++)
            {
                var configuredHero = AllyChannelState.GetEnemyHero(slot);
                if (!String.IsNullOrEmpty(configuredHero)
                    && configuredHero.Equals(heroName, StringComparison.OrdinalIgnoreCase))
                {
                    return slot;
                }
            }
            return null;
        }

        private static Int32? ParseTimerId(String message)
        {
            if (message.Equals("START", StringComparison.OrdinalIgnoreCase))
            {
                return 1; // Backward-compatible default.
            }

            if (!message.StartsWith("START", StringComparison.OrdinalIgnoreCase))
            {
                return null;
            }

            var suffix = message.Substring(5).Trim();
            if (Int32.TryParse(suffix, out var timerId) && timerId >= 1 && timerId <= MaxTimerId)
            {
                return timerId;
            }

            return null;
        }
    }
}
