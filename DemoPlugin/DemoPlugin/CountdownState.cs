namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Linq;
    using System.Timers;

    internal static class CountdownState
    {
        private const Int32 StartSeconds = 10;
        private const Int32 TimerCount = 5;  // 5v5: 5 enemies

        private static readonly Object LockObject = new Object();
        private static readonly Timer[] Timers;

        private static readonly Int32[] RemainingSeconds = Enumerable.Repeat(StartSeconds, TimerCount).ToArray();
        private static readonly Boolean[] IsRunning = new Boolean[TimerCount];

        static CountdownState()
        {
            Timers = new Timer[TimerCount];
            for (var timerId = 1; timerId <= TimerCount; timerId++)
            {
                var capturedId = timerId;
                var timer = new Timer(1000);
                timer.AutoReset = true;
                timer.Elapsed += (_, __) => OnTimerElapsed(capturedId);
                Timers[timerId - 1] = timer;
            }
        }

        public static event Action<Int32> StateChanged;

        public static void StartCountdown(Int32 timerId)
        {
            var index = ValidateTimerId(timerId);
            lock (LockObject)
            {
                RemainingSeconds[index] = StartSeconds;
                IsRunning[index] = true;
                Timers[index].Start();
            }

            RaiseStateChanged(timerId);
        }

        public static (Int32 Seconds, Boolean IsRunning) GetSnapshot(Int32 timerId)
        {
            var index = ValidateTimerId(timerId);
            lock (LockObject)
            {
                return (RemainingSeconds[index], IsRunning[index]);
            }
        }

        private static void OnTimerElapsed(Int32 timerId)
        {
            var index = ValidateTimerId(timerId);
            lock (LockObject)
            {
                if (!IsRunning[index])
                {
                    return;
                }

                RemainingSeconds[index]--;
                if (RemainingSeconds[index] <= 0)
                {
                    RemainingSeconds[index] = 0;
                    IsRunning[index] = false;
                    Timers[index].Stop();
                }
            }

            RaiseStateChanged(timerId);
        }

        private static Int32 ValidateTimerId(Int32 timerId)
        {
            if (timerId < 1 || timerId > TimerCount)
            {
                throw new ArgumentOutOfRangeException(nameof(timerId), $"Timer id must be 1-{TimerCount}");
            }

            return timerId - 1;
        }

        private static void RaiseStateChanged(Int32 timerId)
            => StateChanged?.Invoke(timerId);
    }
}
