namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Net.Sockets;
    using System.Text;

    /// <summary>
    /// Base class for the 4 ally channel buttons on the Creative Console.
    /// Pressing = switch audio to that ally only. Pressing again = back to broadcast ALL.
    /// The button shows the ally's role label and highlights when targeted.
    /// </summary>
    public abstract class AllyChannelCommandBase : PluginDynamicCommand
    {
        private const Int32 LOCAL_IPC_PORT = 5006;
        private readonly Int32 _slotId; // 1-based (1-4)
        private UdpClient _udpClient;

        protected AllyChannelCommandBase(Int32 slotId, String displayName)
            : base(displayName: displayName, description: $"Toggle voice to ally slot {slotId}", groupName: "Voice Channels")
        {
            this._slotId = slotId;
            this._udpClient = new UdpClient();
            AllyChannelState.StateChanged += this.OnStateChanged;
        }

        protected override void RunCommand(String actionParameter)
        {
            // Toggle: if currently targeting this ally → ALL, else → this ally
            AllyChannelState.ToggleTarget(this._slotId);

            // Send IPC to Python client
            var msg = $"PTT_ALLY{this._slotId}_TOGGLE";
            var data = Encoding.UTF8.GetBytes(msg);
            this._udpClient.Send(data, data.Length, "127.0.0.1", LOCAL_IPC_PORT);
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            var role = AllyChannelState.GetAllyRole(this._slotId);
            var label = String.IsNullOrEmpty(role) ? $"Ally {this._slotId}" : role;
            var active = AllyChannelState.IsTargeted(this._slotId);
            return active ? $"🎤 {label}" : label;
        }

        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var role = AllyChannelState.GetAllyRole(this._slotId);
            if (!String.IsNullOrEmpty(role))
            {
                try
                {
                    var fileName = $"{role.ToLower()}_channel.png";
                    var resourcePath = PluginResources.FindFile(fileName);
                    return PluginResources.ReadImage(resourcePath);
                }
                catch
                {
                    // No role-specific image; fall through to default.
                }
            }
            return null;
        }

        private void OnStateChanged(Int32 changedSlot)
        {
            // Refresh when any slot changes (since single-target affects all buttons)
            this.ActionImageChanged();
        }
    }

    // ── 4 concrete subclasses (one per ally) ────────────────────

    public class AllyChannel1Command : AllyChannelCommandBase
    {
        public AllyChannel1Command() : base(1, "Ally Channel 1") { }
    }

    public class AllyChannel2Command : AllyChannelCommandBase
    {
        public AllyChannel2Command() : base(2, "Ally Channel 2") { }
    }

    public class AllyChannel3Command : AllyChannelCommandBase
    {
        public AllyChannel3Command() : base(3, "Ally Channel 3") { }
    }

    public class AllyChannel4Command : AllyChannelCommandBase
    {
        public AllyChannel4Command() : base(4, "Ally Channel 4") { }
    }
}
