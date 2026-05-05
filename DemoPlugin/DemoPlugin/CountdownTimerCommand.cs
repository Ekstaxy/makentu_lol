namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Collections.Generic;

    public class CountdownTimerCommand : PluginDynamicCommand
    {
        private const Int32 StartSeconds = 10;

        private readonly Dictionary<Int32, String> _frameResources = new Dictionary<Int32, String>();

        public CountdownTimerCommand()
            : base(displayName: "Countdown Timer", description: "Counts down from 10 to 0", groupName: "Timers")
        {
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
            CountdownState.StartCountdown();
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, isRunning) = CountdownState.GetSnapshot();
            var status = isRunning ? "Running" : (seconds == 0 ? "Done" : "Ready");
            return $"Timer {seconds}s ({status})";
        }

        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var (seconds, _) = CountdownState.GetSnapshot();

            if (this._frameResources.TryGetValue(seconds, out var resourcePath))
            {
                return PluginResources.ReadImage(resourcePath);
            }

            // Falls back to default icon template if the expected frame image is missing.
            return null;
        }

        private void OnCountdownStateChanged()
            => this.ActionImageChanged();
    }
}
