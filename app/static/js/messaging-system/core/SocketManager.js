/**
 * Socket Manager
 * Handles WebSocket connections and events
 */
export class SocketManager {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
        this.socket = null;
        this.isTyping = false;
        this.typingTimeout = null;
    }

    /**
     * Initialize Socket.IO connection
     */
    initialize() {
        this.socket = io();

        this.socket.on("connect", () => {
            console.log("Connected to messaging system");
            this.socket.emit("join_user_room");
        });

        this.socket.on("new_message", (data) => {
            this.messageSystem.handleNewMessage(data);
        });

        this.socket.on("user_typing", (data) => {
            this.messageSystem.handleTypingIndicator(data);
        });

        this.socket.on("disconnect", () => {
            console.log("Disconnected from messaging system");
        });
    }

    /**
     * Start typing indicator
     */
    startTyping(recipientId) {
        if (!this.isTyping) {
            this.isTyping = true;
            this.socket?.emit("typing_start", {
                recipient_id: recipientId,
            });
        }

        // Clear existing timeout and set new one
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.stopTyping(recipientId);
        }, 3000);
    }

    /**
     * Stop typing indicator
     */
    stopTyping(recipientId) {
        if (this.isTyping) {
            this.isTyping = false;
            this.socket?.emit("typing_stop", {
                recipient_id: recipientId,
            });
        }
        clearTimeout(this.typingTimeout);
    }

    /**
     * Disconnect socket
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}
