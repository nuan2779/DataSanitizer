// Escape untrusted dataset strings before inserting them via innerHTML.
export function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[char]);
}
