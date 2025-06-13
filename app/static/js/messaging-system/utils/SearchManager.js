/**
 * Search Manager
 * Handles search functionality for conversations
 */
export class SearchManager {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
    }

    /**
     * Setup search functionality
     */
    setupSearch() {
        const searchInput = document.getElementById("chatSearch");
        if (!searchInput) return;

        searchInput.addEventListener("input", (e) => {
            this.performSearch(e.target.value);
        });
    }

    /**
     * Perform search on conversations
     */
    performSearch(searchTerm) {
        const normalizedTerm = searchTerm.toLowerCase();
        const chatItems = document.querySelectorAll("#chatItems > div");

        chatItems.forEach((item) => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(normalizedTerm)
                ? "flex"
                : "none";
        });
    }

    /**
     * Clear search
     */
    clearSearch() {
        const searchInput = document.getElementById("chatSearch");
        if (searchInput) {
            searchInput.value = "";
            this.performSearch("");
        }
    }
}
