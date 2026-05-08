namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Net.Sockets;
    using System.Text;

    public class PushToTalkAllCommand : PluginDynamicCommand
    {
        private const int LOCAL_IPC_PORT = 5006;
        private UdpClient udpClient;

        public PushToTalkAllCommand()
            : base(displayName: "PTT: All (Broadcast)", description: "Push to talk to everyone", groupName: "Tactical Voice")
        {
            this.udpClient = new UdpClient();
        }

        protected override Boolean OnLoad()
        {
            return base.OnLoad();
        }

        protected override void RunCommand(String actionParameter)
        {
            // Optional: for toggle logic if it's not a press/release
        }

        // When the Logi Console button is pressed DOWN
        protected override Boolean ProcessButtonEvent2(String actionParameter, DeviceButtonEvent2 buttonEvent)
        {
            if (buttonEvent.EventType == DeviceButtonEventType.Press)
            {
                byte[] data = Encoding.UTF8.GetBytes("PTT_ALL_START");
                this.udpClient.Send(data, data.Length, "127.0.0.1", LOCAL_IPC_PORT);
                return true;
            }
            else if (buttonEvent.EventType == DeviceButtonEventType.Release)
            {
                byte[] data = Encoding.UTF8.GetBytes("PTT_STOP");
                this.udpClient.Send(data, data.Length, "127.0.0.1", LOCAL_IPC_PORT);
                return true;
            }
            return false;
        }
    }
}