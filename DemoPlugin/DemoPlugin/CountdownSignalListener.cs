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

                    if (message.Equals("START", StringComparison.OrdinalIgnoreCase))
                    {
                        CountdownState.StartCountdown();
                        PluginLog.Info($"Countdown started from UDP signal ({result.RemoteEndPoint})");
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
    }
}
