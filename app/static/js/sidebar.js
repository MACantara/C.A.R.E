// Simple sidebar functionality - no animations
function toggleSidebar() {
  const fullSidebar = document.querySelector(".sidebar-full");
  const collapsedSidebar = document.getElementById("collapsed-sidebar");
  const isCurrentlyCollapsed = fullSidebar.style.display === "none";

  if (isCurrentlyCollapsed) {
    // Show full sidebar instantly
    fullSidebar.style.display = "flex";
    collapsedSidebar.style.display = "none";
    localStorage.setItem("sidebarCollapsed", "false");
  } else {
    // Show collapsed sidebar instantly
    fullSidebar.style.display = "none";
    collapsedSidebar.style.display = "flex";
    localStorage.setItem("sidebarCollapsed", "true");
  }
}

// Update sidebar time
function updateSidebarTime() {
  const sidebarTime = document.getElementById("sidebar-time");
  if (sidebarTime && window.timezoneManager) {
    const userTimezone = window.timezoneManager.getUserTimezone();
    const now = new Date();
    const timeString = now.toLocaleTimeString("en-US", {
      timeZone: userTimezone,
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    sidebarTime.textContent = timeString;
  }
}

// Update unread message count
function updateUnreadCount() {
  if (window.socket && typeof window.socket.emit === "function") {
    window.socket.emit("request_unread_count");
  }
}

// Listen for unread count updates
if (window.socket) {
  window.socket.on("unread_count_update", function (data) {
    const count = data.count || 0;

    // Use the correct IDs from the messages-icon partial
    const unreadBadge = document.getElementById("unread-messages-count");
    const collapsedBadge = document.getElementById("collapsed-unread-count");

    if (unreadBadge) {
      if (count > 0) {
        unreadBadge.textContent = count > 99 ? "99+" : count;
        unreadBadge.classList.remove("hidden");
      } else {
        unreadBadge.classList.add("hidden");
      }
    }

    if (collapsedBadge) {
      if (count > 0) {
        collapsedBadge.textContent = count > 9 ? "9+" : count;
        collapsedBadge.classList.remove("hidden");
      } else {
        collapsedBadge.classList.add("hidden");
      }
    }
  });
} else {
  // Fallback to REST API if Socket.IO is not available
  function updateUnreadCountFallback() {
    fetch("/messages/api/unread_count")
      .then((response) => response.json())
      .then((data) => {
        const count = data.count || 0;
        const unreadBadge = document.getElementById("unread-messages-count");
        const collapsedBadge = document.getElementById(
          "collapsed-unread-count"
        );

        if (unreadBadge) {
          if (count > 0) {
            unreadBadge.textContent = count > 99 ? "99+" : count;
            unreadBadge.classList.remove("hidden");
          } else {
            unreadBadge.classList.add("hidden");
          }
        }

        if (collapsedBadge) {
          if (count > 0) {
            collapsedBadge.textContent = count > 9 ? "9+" : count;
            collapsedBadge.classList.remove("hidden");
          } else {
            collapsedBadge.classList.add("hidden");
          }
        }
      })
      .catch((error) => console.error("Error fetching message count:", error));
  }

  // Use REST API fallback
  setTimeout(updateUnreadCountFallback, 1000);
  setInterval(updateUnreadCountFallback, 30000);
}

// Simple initialization - no fade effects
document.addEventListener("DOMContentLoaded", function () {
  const fullSidebar = document.querySelector(".sidebar-full");
  const collapsedSidebar = document.getElementById("collapsed-sidebar");
  const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";

  // Set initial state instantly
  if (isCollapsed) {
    fullSidebar.style.display = "none";
    collapsedSidebar.style.display = "flex";
  } else {
    fullSidebar.style.display = "flex";
    collapsedSidebar.style.display = "none";
  }

  // No fade-in animation - sidebar shows immediately

  // Update time every minute
  updateSidebarTime();
  setInterval(updateSidebarTime, 60000);

  // Request initial unread count
  setTimeout(updateUnreadCount, 1000);

  // Update unread count periodically
  setInterval(updateUnreadCount, 30000); // Every 30 seconds
});
