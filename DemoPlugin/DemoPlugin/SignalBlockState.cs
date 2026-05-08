namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Timers;

    internal static class SignalBlockState
    {
        private static readonly Object LockObject = new Object();
        private static readonly Timer BlinkTimer;

        private static Boolean _upperRightActive;
        private static Boolean _bottomRightActive;
        private static Boolean _phaseOn;

        static SignalBlockState()
        {
            BlinkTimer = new Timer(500);
            BlinkTimer.AutoReset = true;
            BlinkTimer.Elapsed += OnBlinkTimerElapsed;
        }

        public static event Action StateChanged;

        public static void HandleSignal(String message)
        {
            if (String.IsNullOrWhiteSpace(message))
            {
                return;
            }

            var shouldNotify = false;
            lock (LockObject)
            {
                if (message.Equals("1-1", StringComparison.OrdinalIgnoreCase))
                {
                    _upperRightActive = true;
                    shouldNotify = true;
                }
                else if (message.Equals("1-2", StringComparison.OrdinalIgnoreCase))
                {
                    _bottomRightActive = true;
                    shouldNotify = true;
                }
                else if (message.Equals("1-0", StringComparison.OrdinalIgnoreCase))
                {
                    _upperRightActive = false;
                    _bottomRightActive = false;
                    _phaseOn = false;
                    shouldNotify = true;
                }
                else
                {
                    return;
                }

                if (_upperRightActive || _bottomRightActive)
                {
                    BlinkTimer.Start();
                }
                else
                {
                    BlinkTimer.Stop();
                }
            }

            if (shouldNotify)
            {
                RaiseStateChanged();
            }
        }

        public static String GetOverlayKey()
        {
            lock (LockObject)
            {
                if (!_upperRightActive && !_bottomRightActive)
                {
                    return "idle";
                }

                var upperRight = _upperRightActive ? (_phaseOn ? "y" : "p") : "none";
                var bottomRight = _bottomRightActive ? (_phaseOn ? "g" : "r") : "none";
                return $"ur_{upperRight}_br_{bottomRight}";
            }
        }

        private static void OnBlinkTimerElapsed(Object sender, ElapsedEventArgs e)
        {
            lock (LockObject)
            {
                if (!_upperRightActive && !_bottomRightActive)
                {
                    _phaseOn = false;
                    BlinkTimer.Stop();
                    return;
                }

                _phaseOn = !_phaseOn;
            }

            RaiseStateChanged();
        }

        private static void RaiseStateChanged()
            => StateChanged?.Invoke();
    }
}
