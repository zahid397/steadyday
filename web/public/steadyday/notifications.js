const reminderKey = "steadyday.lastNotificationDay";
let lastDay;

export function notificationPermission() {
  return window.isSecureContext && "Notification" in window ? Notification.permission : "unsupported";
}

export async function requestReminderPermission() {
  if (notificationPermission() !== "default") return notificationPermission();
  try {
    return await Notification.requestPermission();
  } catch {
    return "unsupported";
  }
}

export function showReminderNotification(day, { title, body }) {
  if (notificationPermission() !== "granted" || lastDay === day) return false;
  try {
    if (localStorage.getItem(reminderKey) === day) return false;
  } catch {}

  try {
    new Notification(title, { body, icon: "/steadyday/mark.svg", tag: "steadyday-check-in-" + day });
  } catch {
    return false;
  }

  lastDay = day;
  try { localStorage.setItem(reminderKey, day); } catch {}
  return true;
}
