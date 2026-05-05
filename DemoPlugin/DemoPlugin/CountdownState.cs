namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Timers;

    internal static class CountdownState
    {
        private const Int32 StartSeconds = 10;

        private static readonly Object LockObject = new Object();
        private static readonly Timer Timer;

        private static Int32 _remainingSeconds = StartSeconds;
        private static Boolean _isRunning;

        static CountdownState()
        {
            Timer = new Timer(1000);
            Timer.AutoReset = true;
            Timer.Elapsed += OnTimerElapsed;
        }

        public static event Action StateChanged;

        public static void StartCountdown()
        {
            lock (LockObject)
            {
                _remainingSeconds = StartSeconds;
                _isRunning = true;
                Timer.Start();
            }

            RaiseStateChanged();
        }

        public static (Int32 Seconds, Boolean IsRunning) GetSnapshot()
        {
            lock (LockObject)
            {
                return (_remainingSeconds, _isRunning);
            }
        }

        private static void OnTimerElapsed(Object sender, ElapsedEventArgs e)
        {
            lock (LockObject)
            {
                if (!_isRunning)
                {
                    return;
                }

                _remainingSeconds--;
                if (_remainingSeconds <= 0)
                {
                    _remainingSeconds = 0;
                    _isRunning = false;
                    Timer.Stop();
                }
            }

            RaiseStateChanged();
        }

        private static void RaiseStateChanged()
            => StateChanged?.Invoke();
    }
}
