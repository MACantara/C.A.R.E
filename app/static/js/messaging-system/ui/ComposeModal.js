/**
 * Compose Modal
 * Handles compose modal functionality
 */
export class ComposeModal {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
    }

    /**
     * Open compose modal
     */
    open() {
        const modal = document.getElementById("composeModal");
        modal?.classList.remove("hidden");
    }

    /**
     * Close compose modal
     */
    close() {
        const modal = document.getElementById("composeModal");
        const form = document.getElementById("composeForm");

        modal?.classList.add("hidden");
        form?.reset();
    }

    /**
     * Populate recipient select in compose modal
     */
    populateRecipientSelect(users) {
        const select = document.getElementById("composeRecipient");
        if (!select) return;

        select.innerHTML = '<option value="">Select recipient...</option>';

        users.forEach((user) => {
            const option = document.createElement("option");
            option.value = user.id;
            option.textContent = `${user.first_name} ${user.last_name} - ${
                user.role.charAt(0).toUpperCase() + user.role.slice(1)
            }`;
            select.appendChild(option);
        });
    }

    /**
     * Send new message from compose modal
     */
    async sendNewMessage() {
        const form = document.getElementById("composeForm");
        if (!form) return;

        const formData = new FormData(form);

        const messageData = {
            recipient_id: formData.get("recipient_id"),
            subject: formData.get("subject"),
            content: formData.get("content"),
            priority: formData.get("priority"),
            message_type: "general",
        };

        const result =
            await this.messageSystem.conversationManager.sendNewMessage(
                messageData
            );

        if (result.success) {
            this.close();
            // Open the new conversation
            this.messageSystem.openChat(result.recipientId);
        } else {
            console.error("Failed to send message:", result.error);
            // Could show error message to user here
        }
    }
}
