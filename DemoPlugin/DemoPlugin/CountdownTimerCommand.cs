namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Collections.Generic;

    public abstract class CountdownTimerCommandBase : PluginDynamicCommand
    {
        private static readonly String[] CharacterNamesByTimerId =
        {
            "蓋倫",
            "安妮",
            "好運姐",
            "阿姆姆",
            "雷歐娜",
            "墨菲特",
            "馬爾札哈",
            "艾希",
            "沃維克",
            "索娜",
        };

        private readonly Int32 _timerId;
        private readonly Dictionary<Int32, String> _frameResources = new Dictionary<Int32, String>();
        private readonly Byte[] _characterImageBytes;
        private readonly Byte[] _topSkillImageBytes;
        private readonly Byte[] _bottomSkillImageBytes;

        protected CountdownTimerCommandBase(Int32 timerId, String displayName)
            : base(displayName: displayName, description: "閃現 / 傳送 各一組倒數", groupName: "Timers")
        {
            this._timerId = timerId;

            Byte[] characterBytes = null;
            if (timerId >= 1 && timerId <= CharacterNamesByTimerId.Length)
            {
                characterBytes = LoadResourceBytes(
                    $"{CharacterNamesByTimerId[timerId - 1]}.png",
                    $"{CharacterNamesByTimerId[timerId - 1]}_70.png");
            }

            this._characterImageBytes = characterBytes;
            this._topSkillImageBytes = LoadResourceBytes("閃現.png", "閃現.PNG");
            this._bottomSkillImageBytes = LoadResourceBytes("傳送.PNG", "傳送.png");

            for (var seconds = 0; seconds <= 10; seconds++)
            {
                var fileName = $"countdown_{seconds:00}.png";
                try
                {
                    var resourcePath = PluginResources.FindFile(fileName);
                    this._frameResources[seconds] = resourcePath;
                }
                catch
                {
                }
            }

            CountdownState.StateChanged += this.OnCountdownStateChanged;
            if (this._timerId == 1)
            {
                SignalBlockState.StateChanged += this.OnSignalStateChanged;
            }
        }

        protected override void RunCommand(String actionParameter)
        {
            CountdownState.StartCountdown(this._timerId, CountdownSkill.Flash);
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            return String.Empty;
        }

        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var (fSec, fRun) = CountdownState.GetSnapshot(this._timerId, CountdownSkill.Flash);
            var (tSec, tRun) = CountdownState.GetSnapshot(this._timerId, CountdownSkill.Teleport);
            var overlayKey = SignalBlockState.GetOverlayKey();

            if (this._characterImageBytes != null && this._characterImageBytes.Length > 0)
            {
                var composed = SkillCountdownImageComposer.TryBuild(
                    this._timerId,
                    this._characterImageBytes,
                    this._topSkillImageBytes,
                    this._bottomSkillImageBytes,
                    fSec,
                    fRun,
                    tSec,
                    tRun,
                    overlayKey);
                if (composed != null)
                {
                    return composed;
                }
            }

            var frameSec = fRun ? fSec : (tRun ? tSec : Math.Max(fSec, tSec));
            if (this._frameResources.TryGetValue(frameSec, out var resourcePath))
            {
                return PluginResources.ReadImage(resourcePath);
            }

            return null;
        }

        private static Byte[] LoadResourceBytes(params String[] candidates)
        {
            foreach (var candidate in candidates)
            {
                try
                {
                    return PluginResources.ReadBinaryFile(PluginResources.FindFile(candidate));
                }
                catch
                {
                }
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
    }

    public class CountdownTimer1Command : CountdownTimerCommandBase
    {
        public CountdownTimer1Command()
            : base(1, "Countdown Timer 1")
        {
        }
    }

    public class CountdownTimer2Command : CountdownTimerCommandBase
    {
        public CountdownTimer2Command()
            : base(2, "Countdown Timer 2")
        {
        }
    }

    public class CountdownTimer3Command : CountdownTimerCommandBase
    {
        public CountdownTimer3Command()
            : base(3, "Countdown Timer 3")
        {
        }
    }

    public class CountdownTimer4Command : CountdownTimerCommandBase
    {
        public CountdownTimer4Command()
            : base(4, "Countdown Timer 4")
        {
        }
    }

    public class CountdownTimer5Command : CountdownTimerCommandBase
    {
        public CountdownTimer5Command()
            : base(5, "Countdown Timer 5")
        {
        }
    }

    public class CountdownTimer6Command : CountdownTimerCommandBase
    {
        public CountdownTimer6Command()
            : base(6, "Countdown Timer 6")
        {
        }
    }

    public class CountdownTimer7Command : CountdownTimerCommandBase
    {
        public CountdownTimer7Command()
            : base(7, "Countdown Timer 7")
        {
        }
    }

    public class CountdownTimer8Command : CountdownTimerCommandBase
    {
        public CountdownTimer8Command()
            : base(8, "Countdown Timer 8")
        {
        }
    }

    public class CountdownTimer9Command : CountdownTimerCommandBase
    {
        public CountdownTimer9Command()
            : base(9, "Countdown Timer 9")
        {
        }
    }

    public class CountdownTimer10Command : CountdownTimerCommandBase
    {
        public CountdownTimer10Command()
            : base(10, "Countdown Timer 10")
        {
        }
    }
}
