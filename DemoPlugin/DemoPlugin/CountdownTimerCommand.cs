namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Collections.Generic;

    public abstract class CountdownTimerCommandBase : PluginDynamicCommand
    {
        private const Int32 StartSeconds = 10;

        private readonly Int32 _timerId;
        private readonly Dictionary<Int32, String> _frameResources = new Dictionary<Int32, String>();

        protected CountdownTimerCommandBase(Int32 timerId, String displayName)
            : base(displayName: displayName, description: "Counts down from 10 to 0", groupName: "Timers")
        {
            this._timerId = timerId;

            // Load expected frame names explicitly so plugin load stays robust.
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

            CountdownState.StateChanged += this.OnCountdownStateChanged;
        }

        protected override void RunCommand(String actionParameter)
        {
            CountdownState.StartCountdown(this._timerId);
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, isRunning) = CountdownState.GetSnapshot(this._timerId);
            var status = isRunning ? "Running" : (seconds == 0 ? "Done" : "Ready");
            return $"T{this._timerId} {seconds}s ({status})";
        }

        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, _) = CountdownState.GetSnapshot(this._timerId);

            if (this._frameResources.TryGetValue(seconds, out var resourcePath))
            {
                return PluginResources.ReadImage(resourcePath);
            }

            // Falls back to default icon template if the expected frame image is missing.
            return null;
        }

        private void OnCountdownStateChanged(Int32 changedTimerId)
        {
            if (changedTimerId == this._timerId)
            {
                this.ActionImageChanged();
            }
        }
    }

    public class CountdownTimer1Command : CountdownTimerCommandBase
    {
        public CountdownTimer1Command() : base(1, "Countdown Timer 1")
        {
        }
    }

    public class CountdownTimer2Command : CountdownTimerCommandBase
    {
        public CountdownTimer2Command() : base(2, "Countdown Timer 2")
        {
        }
    }

    public class CountdownTimer3Command : CountdownTimerCommandBase
    {
        public CountdownTimer3Command() : base(3, "Countdown Timer 3")
        {
        }
    }

    public class CountdownTimer4Command : CountdownTimerCommandBase
    {
        public CountdownTimer4Command() : base(4, "Countdown Timer 4")
        {
        }
    }

    public class CountdownTimer5Command : CountdownTimerCommandBase
    {
        public CountdownTimer5Command() : base(5, "Countdown Timer 5")
        {
        }
    }

    public class CountdownTimer6Command : CountdownTimerCommandBase
    {
        public CountdownTimer6Command() : base(6, "Countdown Timer 6")
        {
        }
    }

    public class CountdownTimer7Command : CountdownTimerCommandBase
    {
        public CountdownTimer7Command() : base(7, "Countdown Timer 7")
        {
        }
    }

    public class CountdownTimer8Command : CountdownTimerCommandBase
    {
        public CountdownTimer8Command() : base(8, "Countdown Timer 8")
        {
        }
    }

    public class CountdownTimer9Command : CountdownTimerCommandBase
    {
        public CountdownTimer9Command() : base(9, "Countdown Timer 9")
        {
        }
    }

    public class CountdownTimer10Command : CountdownTimerCommandBase
    {
        public CountdownTimer10Command() : base(10, "Countdown Timer 10")
        {
        }
    }
}
