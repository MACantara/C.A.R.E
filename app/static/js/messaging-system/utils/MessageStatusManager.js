/**
 * Message Status Manager
 * Handles message status updates and visual indicators
 */
export class MessageStatusManager {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
        this.messageStatusMap = new Map(); // Track message statuses
    }

    /**
     * Update message status
     */
    updateMessageStatus(messageId, status, realMessageId = null) {
        // Update internal tracking
        this.messageStatusMap.set(messageId, status);

        // Find message element and update status indicator
        const messageElement = document.querySelector(
            `[data-message-id="${messageId}"]`
        );
        if (messageElement) {
            const statusIndicator = messageElement.querySelector(
                "[data-status-indicator]"
            );
            if (statusIndicator) {
                statusIndicator.innerHTML = this.getStatusIcon(status);
            }

            // Update message ID if we got the real ID from server
            if (realMessageId) {
                messageElement.setAttribute("data-message-id", realMessageId);
                this.messageStatusMap.set(realMessageId, status);
                this.messageStatusMap.delete(messageId);
            }
        }
    }

    /**
     * Get status icon HTML
     */
    getStatusIcon(status) {
        const icons = {
            sending: `<i class="bi bi-clock text-xs opacity-60" title="Sending..."></i>`,
            sent: `<i class="bi bi-check text-xs opacity-60" title="Sent"></i>`,
            delivered: `<i class="bi bi-check-all text-xs opacity-60" title="Delivered"></i>`,
            read: `<i class="bi bi-check-all text-xs text-blue-200" title="Read"></i>`,
            failed: `<i class="bi bi-exclamation-triangle text-xs text-red-300 cursor-pointer" title="Failed to send - Click to retry"></i>`,
        };

        return icons[status] || icons["sent"];
    }

    /**
     * Get message status
     */
    getMessageStatus(messageId) {
        return this.messageStatusMap.get(messageId) || "unknown";
    }

    /**
     * Mark all messages from a user as read
     */
    markUserMessagesAsRead(userId) {
        const messageElements = document.querySelectorAll("[data-message-id]");
        messageElements.forEach((element) => {
            const messageId = element.getAttribute("data-message-id");
            // Only update if it's our own message and not already read
            if (this.messageStatusMap.get(messageId) === "delivered") {
                this.updateMessageStatus(messageId, "read");
            }
        });
    }

    /**
     * Clear status tracking for conversation
     */
    clearConversationStatus() {
        this.messageStatusMap.clear();
    }
}
