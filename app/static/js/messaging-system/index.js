import { MessageSystem } from "./core/MessageSystem.js";

/**
 * Main entry point for the messaging system
 * Initializes the system when DOM is loaded
 */
document.addEventListener("DOMContentLoaded", () => {
    // Only initialize if we're on a page that needs messaging
    if (document.querySelector("[data-current-user-id]")) {
        window.messageSystem = new MessageSystem();
    }
});

// Export for external use if needed
export { MessageSystem };
