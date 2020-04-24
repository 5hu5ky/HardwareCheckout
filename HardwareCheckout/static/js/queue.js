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

    start: function() {
        // TODO change to wss
        var url = "ws://" + location.host + "/queue/event";
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            console.log(event);
            msg = JSON.parse(event.data);
            if (msg.type == "new_device") {
                updater.notify("Your device " + msg.device.name + " is ready. You have five minutes to log in before the device becomes available to the next person in the queue.");
                updater.addConnectionInfo(msg.device); // TODO: create this method
            }
            if (msg.type == "all_devices") {
                updater.removeAll();
                for (let device of msg.devices) {
                    updater.addConnectionInfo(device);
                }
            }
            if(msg.error && msg.error == "success" )
            {
                if (msg.message == "device_available") {
                    updater.notify("Your device " + msg.device + " is ready. You have five minutes to log in before the device becomes available to the next person in the queue.");
                } else if (msg.message == "device_lost") {
                    updater.notify("Your login time for device " + msg.device + " has expired. You may re-enter the queue to try again.");
                } else if (msg.message == "device_reclaimed") {
                    updater.notify("Thank you for participating in the virtual CHV CTF. If you would like more time, you may enter the queue again.");
                }
            } else if (msg.error) {
                updater.notify(msg.error);
            }
        }
    },

    notify: function(msg, connection) {
        updater.showMessage(connection)
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification(msg);
        } else {
            alert(msg);
        }
    },

    removeConnectionInfo: function(connection) {
        device = document.getElementById(connection.device);
        updater.removeAll(device);
        list = domDevices.querySelector("ul");
        if (!list.hasChildNodes())
        {
            domDevices.style.display = "none";
        }
    },

    removeAll: function(e) {
        var child = parent.lastElementChild;  
        while (child) { 
            updater.removeAll(child);
            parent.removeChild(child);
            child = parent.lastElementChild; 
        } 
    },

    showConnectionInfo: function(connection) {
        let domDevices = document.getElementById("devices");
        let domList = domDevices.querySelector("ul");
        domList.innerHTML = "";
        domDevices.style.display = "block";
        
        let domSSH = document.createElement("li");
        domSSH.innerText = "SSH: " + connection.ssh;

        let domWebLink = document.createElement("a");
        domWebLink.href = connection.webUrl;
        domWebLink.innerText = connection.webUrl;

        let domWeb = document.createElement("li");
        domWeb.innerText = "Web: ";
        domWeb.appendChild(domWebLink);

        let ul = document.createElement("ul");
        ul.appendChild(domSSH);
        ul.appendChild(domWeb);

        let li = document.createElement("li");
        li.id = connection.device;
        li.innerText = connection.name;
        li.appendChild(ul);

        domList.appendChild(li);
    }
};

updater.start();
