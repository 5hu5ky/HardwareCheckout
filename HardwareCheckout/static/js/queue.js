// function newMessage(form) {
//     var message = form.formToDict();
//     updater.socket.send(JSON.stringify(message));
//     form.find("input[type=text]").val("").select();
// }

// jQuery.fn.formToDict = function() {
//     var fields = this.serializeArray();
//     var json = {}
//     for (var i = 0; i < fields.length; i++) {
//         json[fields[i].name] = fields[i].value;
//     }
//     if (json.next) delete json.next;
//     return json;
// };

var updater = {
    socket: null,

    escapeAttribute: attr => attr.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/\xA0/g, "&nbsp;"),
    escapeHTML: html => html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\xA0/g, "&nbsp;"),

    renderDeviceInfo: function (device) {
        return "<li id=\"device_" +
            updater.escapeAttribute(device.name) + "\">" +
            updater.escapeHTML(device.name) + "<ul><li>SSH: " +
            updater.escapeHTML(device.sshAddr) + "</li><li>Web: <a href=\"" +
            updater.escapeAttribute(device.webUrl) + "\">" +
            updater.escapeHTML(device.webUrl) + "</a></li></ul></li>";
    },

    renderDevices: function (devices) {
        return "<h6>Devices available:</h6><ul>" +
            devices.map(updater.renderDeviceInfo).join("") + "</ul>";
    },

    start: function() {
        // TODO change to wss
        var url = "ws://" + location.host + "/queue/event";
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
                document.getElementById("device_" + msg.device.name).remove();
                if (msg.reason == "queue_timeout") {
                    updater.notify("Your login time for device " + msg.device + " has expired. You may re-enter the queue to try again.");
                } else if (msg.reason == "normal") {
                    updater.notify("Thank you for participating in the virtual CHV CTF. If you would like more time, you may enter the queue again.");
                }
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
