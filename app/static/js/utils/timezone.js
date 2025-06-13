/**
 * Timezone Utility
 * Handles automatic timezone detection and user preference management
 */
class TimezoneManager {
    constructor() {
        this.init();
    }

    /**
     * Initialize timezone management
     */
    init() {
        this.detectAndSetTimezone();
        this.setupTimezoneChangeHandler();
    }

    /**
     * Detect user's timezone and set it on the server
     */
    detectAndSetTimezone() {
        // Get user's timezone from browser
        const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        // Check if it's different from stored timezone
        const storedTimezone = sessionStorage.getItem("user_timezone");

        if (!storedTimezone || storedTimezone !== userTimezone) {
            this.setTimezone(userTimezone);
        }
    }

    /**
     * Set timezone on server
     */
    async setTimezone(timezone) {
        try {
            const response = await fetch("/api/set_timezone", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ timezone: timezone }),
            });

            const data = await response.json();

            if (data.success) {
                sessionStorage.setItem("user_timezone", timezone);
                console.log(`Timezone set to: ${timezone}`);

                // Refresh time displays if any exist
                this.refreshTimeDisplays();
            } else {
                console.error("Failed to set timezone:", data.error);
            }
        } catch (error) {
            console.error("Error setting timezone:", error);
        }
    }

    /**
     * Setup timezone change handler for manual selection
     */
    setupTimezoneChangeHandler() {
        // Add event listener for timezone selectors
        document.addEventListener("change", (e) => {
            if (e.target.matches("[data-timezone-selector]")) {
                this.setTimezone(e.target.value);
            }
        });
    }

    /**
     * Refresh time displays on the page
     */
    refreshTimeDisplays() {
        // Find and update any elements with time data
        const timeElements = document.querySelectorAll("[data-time]");
        timeElements.forEach((element) => {
            const utcTime = element.getAttribute("data-time");
            if (utcTime) {
                const localTime = this.formatTimeToLocal(utcTime);
                element.textContent = localTime;
            }
        });
    }

    /**
     * Format UTC time to user's local timezone
     */
    formatTimeToLocal(utcTimeString, options = {}) {
        try {
            const date = new Date(utcTimeString);
            const userTimezone =
                sessionStorage.getItem("user_timezone") ||
                Intl.DateTimeFormat().resolvedOptions().timeZone;

            const defaultOptions = {
                timeZone: userTimezone,
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                hour12: true,
            };

            const formatOptions = { ...defaultOptions, ...options };
            return date.toLocaleString("en-US", formatOptions);
        } catch (error) {
            console.error("Error formatting time:", error);
            return utcTimeString; // Return original if formatting fails
        }
    }

    /**
     * Get user's current timezone
     */
    getUserTimezone() {
        return (
            sessionStorage.getItem("user_timezone") ||
            Intl.DateTimeFormat().resolvedOptions().timeZone
        );
    }

    /**
     * Format relative time (e.g., "2 hours ago")
     */
    formatRelativeTime(utcTimeString) {
        try {
            const date = new Date(utcTimeString);
            const now = new Date();
            const diffInMinutes = Math.floor((now - date) / (1000 * 60));

            if (diffInMinutes < 1) return "Just now";
            if (diffInMinutes < 60)
                return `${diffInMinutes} minute${
                    diffInMinutes > 1 ? "s" : ""
                } ago`;

            const diffInHours = Math.floor(diffInMinutes / 60);
            if (diffInHours < 24)
                return `${diffInHours} hour${diffInHours > 1 ? "s" : ""} ago`;

            const diffInDays = Math.floor(diffInHours / 24);
            if (diffInDays < 7)
                return `${diffInDays} day${diffInDays > 1 ? "s" : ""} ago`;

            // For older dates, show formatted date
            return this.formatTimeToLocal(utcTimeString, {
                month: "short",
                day: "numeric",
                year: diffInDays > 365 ? "numeric" : undefined,
            });
        } catch (error) {
            console.error("Error formatting relative time:", error);
            return utcTimeString;
        }
    }
}

// Initialize timezone management when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.timezoneManager = new TimezoneManager();
});

// Export for use in other modules
export { TimezoneManager };
