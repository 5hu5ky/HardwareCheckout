var updater = {
    socket: null,
    escapeAttribute: attr => attr.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/\xA0/g, "&nbsp;"),
    escapeHTML: html => html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\xA0/g, "&nbsp;"),

    renderDeviceInfo: function (device) {
        return "<div class=\"available-device\" id=\"device_" + device.id + "\">" +
            "<div class=\"available-device-header\">" +
            "    <div class=\"available-device-header--corner\"></div>" +
            "  <div class=\"available-device-header--name\">" + updater.escapeHTML(device.name) + "</div>" +
            "</div>" +
            "<div class=\"available-device-content\">" +
            "    <div>" +
            "      <div>Your device is ready!  Connect to it using:</div>" +
            "      <div class=\"tab-space\">$" + updater.escapeHTML(device.sshAddr) + "</div>" +
            "      <br>" +
            "      <div>Or visit it at <a href=\"" + updater.escapeAttribute(device.webUrl) + "\">" + updater.escapeHTML(device.webUrl) + "</a></div>" +
            "    </div>" +
            "    <div>Check out the tutorial <a href=\"https://www.carhackingvillage.com/getting-started\">here</a>.</div>" +
            "</div>" +
            "</div>"
    },
    renderDevices: function (devices) {
        return "<div class=\"section-header\">Devices available</div>" +
            "<div class=\"available-devices--row\">" +
            devices.map(updater.renderDeviceInfo).join("") +
            "</div>";
    },
    start: function() {
        if (window.location.protocol === 'https:') {
            var websocket_proto = "wss://"
        } else {
            var websocket_proto = "ws://"
        }
        var url = websocket_proto + location.host + "/queue/event";
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            console.log(event);
            msg = JSON.parse(event.data);
            if (msg.type == "new_device") {
                document.getElementById("devices").lastElementChild.innerHTML += updater.renderDeviceInfo(msg.device);
                updater.notify("Your device " + msg.device.name + " is ready. You have five minutes to log in before the device becomes available to the next person in the queue.");
            } else if (msg.type == "all_devices") {
                document.getElementById("devices").innerHTML = updater.renderDevices(msg.devices);
            } else if (msg.type == "rm_device") {
                document.getElementById("device_" + msg.device.id).remove();
                if (msg.reason == "queue_timeout") {
                    updater.notify("Your login time for device " + msg.device + " has expired. You may re-enter the queue to try again.");
                } else if (msg.reason == "normal") {
                    updater.notify("Thank you for participating in the virtual CHV CTF. If you would like more time, you may enter the queue again.");
                }
            } else if (msg.type == "queue_grow") {
                let count = parseInt(document.getElementById("qs_" + msg.queue).innerText);
                document.getElementById("qs_" + msg.queue).innerText = (count + 1)
            } else if (msg.type == "queue_shrink") {
                let count = parseInt(document.getElementById("qs_" + msg.queue).innerText);
                document.getElementById("qs_" + msg.queue).innerText = (count - 1)
            } else if (msg.error) {
                updater.notify(msg.error);
            }
        }
    },
    notify: function(msg, connection) {
        // updater.showMessage(connection)
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification(msg);
        } else {
            alert(msg);
        }
    }
};
updater.start();

