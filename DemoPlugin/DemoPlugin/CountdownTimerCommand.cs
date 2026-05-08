namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Collections.Generic;

    /// <summary>
    /// Base class for the 5 enemy hero buttons on the Creative Console.
    /// Each button shows the enemy hero image and a countdown overlay
    /// when a summoner spell cooldown is triggered (e.g. TP, Flash).
    /// </summary>
    public abstract class CountdownTimerCommandBase : PluginDynamicCommand
    {
        private const Int32 StartSeconds = 10;

        // Fallback static hero names (overridden by dynamic config from UI).
        private static readonly String[] FallbackHeroNames =
        {
            "蓋倫",
            "安妮",
            "好運姐",
            "阿姆姆",
            "雷歐娜",
        };

        private readonly Int32 _timerId;
        private readonly Dictionary<Int32, String> _frameResources = new Dictionary<Int32, String>();
        private readonly Dictionary<String, String> _countdownOverlayResources = new Dictionary<String, String>();
        private String _characterResourcePath;

        protected CountdownTimerCommandBase(Int32 timerId, String displayName)
            : base(displayName: displayName, description: "Enemy spell countdown", groupName: "Enemy Timers")
        {
            this._timerId = timerId;

            // Try loading character image from fallback names first.
            TryLoadCharacterImage();

            // Load countdown frame images.
            for (var seconds = 0; seconds <= StartSeconds; seconds++)
            {
                var fileName = $"countdown_{seconds:00}.png";
                try
                {
                    var resourcePath = PluginResources.FindFile(fileName);
                    this._frameResources[seconds] = resourcePath;
                }
                catch
                {
                    // Ignore missing frame; fallback icon will be used.
                }
            }

            // Countdown overlays: same countdown base image, only corners differ.
            var overlayKeys = new[]
            {
                "ur_y_br_none",
                "ur_p_br_none",
                "ur_none_br_g",
                "ur_none_br_r",
                "ur_y_br_g",
                "ur_y_br_r",
                "ur_p_br_g",
                "ur_p_br_r",
            };
            foreach (var overlayKey in overlayKeys)
            {
                for (var seconds = 0; seconds <= StartSeconds; seconds++)
                {
                    var fileName = $"countdown_{seconds:00}_{overlayKey}.png";
                    try
                    {
                        this._countdownOverlayResources[$"{seconds:00}:{overlayKey}"] = PluginResources.FindFile(fileName);
                    }
                    catch
                    {
                        // Optional asset; ignore if missing.
                    }
                }
            }

            CountdownState.StateChanged += this.OnCountdownStateChanged;
            if (this._timerId == 1)
            {
                SignalBlockState.StateChanged += this.OnSignalStateChanged;
            }

            // Listen for dynamic config changes to update hero image.
            AllyChannelState.StateChanged += this.OnConfigChanged;
        }

        private void TryLoadCharacterImage()
        {
            // First try dynamic config.
            var heroName = AllyChannelState.GetEnemyHero(this._timerId);

            // Fallback to static list.
            if (String.IsNullOrEmpty(heroName)
                && this._timerId >= 1
                && this._timerId <= FallbackHeroNames.Length)
            {
                heroName = FallbackHeroNames[this._timerId - 1];
            }

            if (!String.IsNullOrEmpty(heroName))
            {
                try
                {
                    this._characterResourcePath = PluginResources.FindFile($"{heroName}_skills.png");
                }
                catch
                {
                    this._characterResourcePath = null;
                }
            }
        }

        protected override void RunCommand(String actionParameter)
        {
            CountdownState.StartCountdown(this._timerId);
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, isRunning) = CountdownState.GetSnapshot(this._timerId);
            var heroName = AllyChannelState.GetEnemyHero(this._timerId);
            if (String.IsNullOrEmpty(heroName) && this._timerId >= 1 && this._timerId <= FallbackHeroNames.Length)
                heroName = FallbackHeroNames[this._timerId - 1];

            var label = String.IsNullOrEmpty(heroName) ? $"E{this._timerId}" : heroName;
            var status = isRunning ? $"{seconds}s" : (seconds == 0 ? "Done" : "Ready");
            return $"{label} ({status})";
        }

        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, _) = CountdownState.GetSnapshot(this._timerId);
            if (this._timerId == 1)
            {
                var overlayKey = SignalBlockState.GetOverlayKey();
                if (!String.Equals(overlayKey, "idle", StringComparison.OrdinalIgnoreCase))
                {
                    var compositeKey = $"{seconds:00}:{overlayKey}";
                    if (this._countdownOverlayResources.TryGetValue(compositeKey, out var overlayResourcePath))
                    {
                        return PluginResources.ReadImage(overlayResourcePath);
                    }
                }
            }

            if (!String.IsNullOrEmpty(this._characterResourcePath))
            {
                return PluginResources.ReadImage(this._characterResourcePath);
            }

            if (this._frameResources.TryGetValue(seconds, out var resourcePath))
            {
                return PluginResources.ReadImage(resourcePath);
            }

            return null;
        }

        private void OnCountdownStateChanged(Int32 changedTimerId)
        {
            if (changedTimerId == this._timerId)
            {
                this.ActionImageChanged();
            }
        }

        private void OnSignalStateChanged()
        {
            if (this._timerId == 1)
            {
                this.ActionImageChanged();
            }
        }

        private void OnConfigChanged(Int32 slot)
        {
            // When enemy config changes, reload the hero image.
            TryLoadCharacterImage();
            this.ActionImageChanged();
        }
    }

    // ── 5 enemy hero timer buttons ──────────────────────────────

    public class CountdownTimer1Command : CountdownTimerCommandBase
    {
        public CountdownTimer1Command() : base(1, "Enemy Timer 1") { }
    }

    public class CountdownTimer2Command : CountdownTimerCommandBase
    {
        public CountdownTimer2Command() : base(2, "Enemy Timer 2") { }
    }

    public class CountdownTimer3Command : CountdownTimerCommandBase
    {
        public CountdownTimer3Command() : base(3, "Enemy Timer 3") { }
    }

    public class CountdownTimer4Command : CountdownTimerCommandBase
    {
        public CountdownTimer4Command() : base(4, "Enemy Timer 4") { }
    }

    public class CountdownTimer5Command : CountdownTimerCommandBase
    {
        public CountdownTimer5Command() : base(5, "Enemy Timer 5") { }
    }
}
