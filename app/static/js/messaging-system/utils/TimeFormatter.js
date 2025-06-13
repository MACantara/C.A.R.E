/**
 * Time Formatter
 * Utility class for formatting timestamps
 */
export class TimeFormatter {
    /**
     * Format timestamp for display
     */
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);

        if (diffInHours < 24) {
            return date.toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
            });
        } else if (diffInHours < 168) {
            // 7 days
            return date.toLocaleDateString("en-US", { weekday: "short" });
        } else {
            return date.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
            });
        }
    }

    /**
     * Format full date and time
     */
    formatFullDateTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
        });
    }

    /**
     * Get relative time (e.g., "2 hours ago")
     */
    getRelativeTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInMinutes = Math.floor((now - date) / (1000 * 60));

        if (diffInMinutes < 1) return "Just now";
        if (diffInMinutes < 60)
            return `${diffInMinutes} minute${diffInMinutes > 1 ? "s" : ""} ago`;

        const diffInHours = Math.floor(diffInMinutes / 60);
        if (diffInHours < 24)
            return `${diffInHours} hour${diffInHours > 1 ? "s" : ""} ago`;

        const diffInDays = Math.floor(diffInHours / 24);
        if (diffInDays < 7)
            return `${diffInDays} day${diffInDays > 1 ? "s" : ""} ago`;

        return this.formatTime(timestamp);
    }
}
