$(document).ready(function() {

    $("#messageform").on("submit", function() {
        newMessage($(this));
        return false;
    });
    $("#messageform").on("keypress", function(e) {
        if (e.keyCode == 13) {
            newMessage($(this));
            return false;
        }
    });
    $("#message").select();
    updater.start();
});

function newMessage(form) {
    var message = form.formToDict();
    updater.socket.send(JSON.stringify(message));
    form.find("input[type=text]").val("").select();
}

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

var updater = {
    socket: null,

    start: function() {
        // TODO change to wss
        var url = "ws://" + location.host + "/queue/";
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            msg = JSON.parse(event.data)
            if (msg.message == "device_available") {
                notify("Your device " + msg.device + " is ready. You have five minutes to log in before the device becomes available to the next person in the queue.");
            } else if (msg.message == "device_lost") {
                notify("Your login time for device " + msg.device + " has expired. You may re-enter the queue to try again.");
            } else if (msg.message == "device_reclaimed") {
                notify("Thank you for participating in the virtual CHV CTF. If you would like more time, you may enter the queue again.");
            }
            
        }
    },

    showMessage: function(message) {
        var existing = $("#m" + message.id);
        if (existing.length > 0) return;
        var node = $(message.html);
        node.hide();
        $("#inbox").append(node);
        node.slideDown();
    }
};