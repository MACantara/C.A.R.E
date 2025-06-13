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
        this.currentTypingRecipient = null;
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

        this.socket.on("message_delivered", (data) => {
            this.messageSystem.handleMessageDelivered(data);
        });

        this.socket.on("message_read", (data) => {
            this.messageSystem.handleMessageRead(data);
        });

        this.socket.on("disconnect", () => {
            console.log("Disconnected from messaging system");
        });
    }

    /**
     * Start typing indicator
     */
    startTyping(recipientId) {
        if (!this.isTyping || this.currentTypingRecipient !== recipientId) {
            this.isTyping = true;
            this.currentTypingRecipient = recipientId;
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
        if (this.isTyping && this.currentTypingRecipient === recipientId) {
            this.isTyping = false;
            this.currentTypingRecipient = null;
            this.socket?.emit("typing_stop", {
                recipient_id: recipientId,
            });
        }
        clearTimeout(this.typingTimeout);
    }

    /**
     * Force stop all typing indicators
     */
    forceStopTyping() {
        if (this.isTyping && this.currentTypingRecipient) {
            this.stopTyping(this.currentTypingRecipient);
        }
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
