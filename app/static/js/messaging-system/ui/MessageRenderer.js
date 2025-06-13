import { TimeFormatter } from "../utils/TimeFormatter.js";

/**
 * Message Renderer
 * Handles rendering of messages and chat interface elements
 */
export class MessageRenderer {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
        this.timeFormatter = new TimeFormatter();
    }

    /**
     * Render chat list in sidebar
     */
    renderChatList(conversations) {
        const container = document.getElementById("chatItems");
        if (!container) return;

        container.innerHTML = "";

        conversations.forEach((conversation) => {
            const chatItem = this.createChatItem(conversation);
            container.appendChild(chatItem);
        });
    }

    /**
     * Create a chat item element
     */
    createChatItem(conversation) {
        const div = document.createElement("div");
        div.className = `flex items-center p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 ${
            this.messageSystem.currentChatUserId === conversation.other_user.id
                ? "bg-blue-50 dark:bg-blue-900/20"
                : ""
        }`;

        div.addEventListener("click", () =>
            this.messageSystem.openChat(conversation.other_user.id)
        );

        const lastMessage = conversation.last_message;
        const timeStr = lastMessage
            ? this.timeFormatter.formatChatListTime(lastMessage.created_at)
            : "";

        // Get full timestamp for tooltip
        const fullTimeStr = lastMessage
            ? this.timeFormatter.formatFullDateTime(lastMessage.created_at)
            : "";

        div.innerHTML = `
            <div class="flex-shrink-0 mr-3">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                    ${conversation.other_user.first_name[0]}${
            conversation.other_user.last_name[0]
        }
                </div>
                ${
                    conversation.unread_count > 0
                        ? '<div class="w-3 h-3 bg-blue-500 rounded-full -mt-2 -ml-2"></div>'
                        : ""
                }
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-medium text-gray-900 dark:text-white truncate">
                        ${conversation.other_user.first_name} ${
            conversation.other_user.last_name
        }
                    </h3>
                    <span class="text-xs text-gray-500 dark:text-gray-400" title="${fullTimeStr}">${timeStr}</span>
                </div>
                <div class="flex items-center justify-between">
                    <p class="text-sm text-gray-500 dark:text-gray-400 truncate">
                        ${
                            lastMessage
                                ? lastMessage.content.length > 40
                                    ? lastMessage.content.substring(0, 40) +
                                      "..."
                                    : lastMessage.content
                                : "No messages yet"
                        }
                    </p>
                    ${
                        conversation.unread_count > 0
                            ? `<span class="ml-2 bg-blue-500 text-white text-xs rounded-full px-2 py-1">${conversation.unread_count}</span>`
                            : ""
                    }
                </div>
            </div>
        `;

        return div;
    }

    /**
     * Render chat header
     */
    renderChatHeader(user) {
        const header = document.getElementById("chatHeader");
        if (!header) return;

        header.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold mr-3">
                        ${user.first_name[0]}${user.last_name[0]}
                    </div>
                    <div>
                        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
                            ${user.first_name} ${user.last_name}
                        </h2>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${
                            user.role.charAt(0).toUpperCase() +
                            user.role.slice(1)
                        }</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="messageSystem.showChatOptions()" class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                        <i class="bi bi-three-dots-vertical"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render messages in the chat area
     */
    renderMessages(messages) {
        const container = document.getElementById("messagesArea");
        if (!container) return;

        container.innerHTML = "";

        messages.forEach((message) => {
            const messageElement = this.createMessageElement(message);
            container.appendChild(messageElement);
        });

        // Scroll to bottom smoothly
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    /**
     * Create a message element
     */
    createMessageElement(message) {
        const isOwn = message.sender_id === this.messageSystem.currentUserId;
        const div = document.createElement("div");
        div.className = `flex ${isOwn ? "justify-end" : "justify-start"} mb-3`;
        div.setAttribute("data-message-id", message.id || message.temp_id);

        const messageTime = this.timeFormatter.formatTime(message.created_at);
        const statusIcon = this.getStatusIcon(message.status || "sent", isOwn);

        // Add timezone-aware timestamp data attributes
        const timestampData = message.created_at
            ? `data-time="${message.created_at}"`
            : "";
        const timezoneData = message.timezone
            ? `data-timezone="${message.timezone}"`
            : "";

        // Get full timestamp and relative time for tooltip
        const fullTimestamp = message.created_at
            ? this.timeFormatter.formatFullDateTime(message.created_at)
            : messageTime;
        const relativeTime = message.created_at
            ? this.timeFormatter.getRelativeTime(message.created_at)
            : "";

        div.innerHTML = `
            <div class="max-w-xs lg:max-w-md ${
                isOwn
                    ? "bg-blue-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            } rounded-lg px-4 py-2 shadow-sm">
                ${
                    !isOwn
                        ? `<p class="text-xs font-medium mb-1 opacity-75">${message.sender_name}</p>`
                        : ""
                }
                <p class="text-sm whitespace-pre-wrap break-words">${
                    message.content
                }</p>
                <div class="flex items-center justify-between mt-1">
                    <p class="text-xs ${
                        isOwn
                            ? "text-blue-100"
                            : "text-gray-500 dark:text-gray-400"
                    } opacity-75 message-time cursor-help" ${timestampData} ${timezoneData} title="${fullTimestamp}${
            relativeTime ? " (" + relativeTime + ")" : ""
        }">
                        ${messageTime}
                    </p>
                    ${
                        isOwn
                            ? `<div class="ml-2 flex items-center space-x-1" data-status-indicator>
                        ${statusIcon}
                    </div>`
                            : ""
                    }
                </div>
            </div>
        `;

        return div;
    }

    /**
     * Get status icon based on message status
     */
    getStatusIcon(status, isOwn) {
        if (!isOwn) return "";

        const icons = {
            sending: `<i class="bi bi-clock text-xs opacity-60" title="Sending..."></i>`,
            sent: `<i class="bi bi-check text-xs opacity-60" title="Sent"></i>`,
            delivered: `<i class="bi bi-check-all text-xs opacity-60" title="Delivered"></i>`,
            read: `<i class="bi bi-check-all text-xs text-blue-200" title="Read"></i>`,
            failed: `<i class="bi bi-exclamation-triangle text-xs text-red-300" title="Failed to send"></i>`,
        };

        return icons[status] || icons["sent"];
    }

    /**
     * Add message to UI immediately
     */
    addMessageToUI(message) {
        const container = document.getElementById("messagesArea");
        if (!container) return;

        const messageElement = this.createMessageElement(message);
        container.appendChild(messageElement);

        // Scroll to bottom smoothly
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }
}
