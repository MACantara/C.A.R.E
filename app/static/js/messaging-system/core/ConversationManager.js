/**
 * Conversation Manager
 * Handles conversation data and API interactions
 */
export class ConversationManager {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
        this.conversations = [];
        this.allUsers = [];
    }

    /**
     * Load conversations from API
     */
    async loadConversations() {
        try {
            const response = await fetch("/messages/api/conversations");
            const data = await response.json();

            this.conversations = data.conversations;
            this.messageSystem.messageRenderer.renderChatList(
                this.conversations
            );
            this.messageSystem.uiManager.hideLoadingState();

            if (this.conversations.length === 0) {
                this.messageSystem.uiManager.showEmptyState();
            } else {
                this.messageSystem.uiManager.showChatItems();
            }
        } catch (error) {
            console.error("Error loading conversations:", error);
            this.messageSystem.uiManager.hideLoadingState();
            this.messageSystem.uiManager.showEmptyState();
        }
    }

    /**
     * Load users from API
     */
    async loadUsers() {
        try {
            const response = await fetch("/messages/api/users");
            const data = await response.json();

            this.allUsers = data.users;
            this.messageSystem.composeModal.populateRecipientSelect(
                this.allUsers
            );
        } catch (error) {
            console.error("Error loading users:", error);
        }
    }

    /**
     * Load messages for a specific conversation
     */
    async loadChatMessages(userId) {
        try {
            const response = await fetch(
                `/messages/api/conversation/${userId}`
            );
            const data = await response.json();

            this.messageSystem.messageRenderer.renderChatHeader(
                data.other_user
            );
            this.messageSystem.messageRenderer.renderMessages(data.messages);
            this.markConversationAsRead(userId);

            // Focus on message input after loading
            setTimeout(() => {
                const input = document.getElementById("messageInput");
                input?.focus();
            }, 100);
        } catch (error) {
            console.error("Error loading chat messages:", error);
        }
    }

    /**
     * Mark conversation as read
     */
    async markConversationAsRead(userId) {
        try {
            await fetch(`/messages/api/mark_conversation_read/${userId}`, {
                method: "POST",
            });
        } catch (error) {
            console.error("Error marking conversation as read:", error);
        }
    }

    /**
     * Send new message via API
     */
    async sendNewMessage(messageData) {
        try {
            const response = await fetch("/messages/api/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(messageData),
            });

            const data = await response.json();

            if (data.success) {
                this.loadConversations();
                return {
                    success: true,
                    recipientId: parseInt(messageData.recipient_id),
                };
            } else {
                console.error("Failed to send message:", data.error);
                return { success: false, error: data.error };
            }
        } catch (error) {
            console.error("Error sending message:", error);
            return { success: false, error: error.message };
        }
    }
}
