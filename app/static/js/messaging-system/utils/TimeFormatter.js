/**
 * Time Formatter
 * Utility class for formatting timestamps with timezone awareness
 */
export class TimeFormatter {
    constructor() {
        this.userTimezone = this.getUserTimezone();
    }

    /**
     * Get user's timezone
     */
    getUserTimezone() {
        return (
            sessionStorage.getItem("user_timezone") ||
            Intl.DateTimeFormat().resolvedOptions().timeZone
        );
    }

    /**
     * Format timestamp for display with actual time
     */
    formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffInHours = (now - date) / (1000 * 60 * 60);

            // Always show actual time, but vary the format based on recency
            if (diffInHours < 24) {
                // Same day - show time only
                return date.toLocaleTimeString("en-US", {
                    timeZone: this.userTimezone,
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                });
            } else if (diffInHours < 168) {
                // Within a week - show day and time
                return date.toLocaleDateString("en-US", {
                    timeZone: this.userTimezone,
                    weekday: "short",
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                });
            } else {
                // Older than a week - show date and time
                return date.toLocaleDateString("en-US", {
                    timeZone: this.userTimezone,
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                    year: diffInHours > 8760 ? "numeric" : undefined, // Show year if > 1 year
                });
            }
        } catch (error) {
            console.error("Error formatting time:", error);
            return new Date(timestamp).toLocaleString();
        }
    }

    /**
     * Format timestamp for chat list (more compact)
     */
    formatChatListTime(timestamp) {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffInHours = (now - date) / (1000 * 60 * 60);

            if (diffInHours < 24) {
                // Same day - show time only
                return date.toLocaleTimeString("en-US", {
                    timeZone: this.userTimezone,
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                });
            } else if (diffInHours < 168) {
                // Within a week - show day only
                return date.toLocaleDateString("en-US", {
                    timeZone: this.userTimezone,
                    weekday: "short",
                });
            } else {
                // Older - show date
                return date.toLocaleDateString("en-US", {
                    timeZone: this.userTimezone,
                    month: "short",
                    day: "numeric",
                    year: diffInHours > 8760 ? "numeric" : undefined,
                });
            }
        } catch (error) {
            console.error("Error formatting chat list time:", error);
            return this.formatTime(timestamp);
        }
    }

    /**
     * Format full date and time with timezone
     */
    formatFullDateTime(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleDateString("en-US", {
                timeZone: this.userTimezone,
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
            });
        } catch (error) {
            console.error("Error formatting full datetime:", error);
            return new Date(timestamp).toLocaleString();
        }
    }

    /**
     * Get relative time (e.g., "2 hours ago") - kept for tooltip use
     */
    getRelativeTime(timestamp) {
        try {
            const date = new Date(timestamp);
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

            return this.formatTime(timestamp);
        } catch (error) {
            console.error("Error formatting relative time:", error);
            return this.formatTime(timestamp);
        }
    }

    /**
     * Update timezone and refresh formatting
     */
    updateTimezone(timezone) {
        this.userTimezone = timezone;
        sessionStorage.setItem("user_timezone", timezone);
    }
}
