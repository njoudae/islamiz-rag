// Links that open a Dorar page at a specific passage instead of at its top.
//
// A text fragment (#:~:text=...) makes the browser scroll to the first place those words
// appear and highlight them. The words must match the page exactly, so only a short opening
// stretch of the stored text is used, and anything the page renders differently is avoided.
// If the words are not found, the page simply opens at the top as before.

const WORDS = 6;

/** The first few words of a passage that are safe to search for on its page. */
export function passageLead(text) {
    // Stop before footnote marks, book citations and verse references, which the page lays out differently.
    const body = String(text || '').split(/\[\d+\]|\(\(|\[/)[0];
    for (let line of body.split(/\n+/)) {
        line = line.replace(/^\s*\d+\s*[-–.]\s*/, '').trim(); // "1- " list numbering
        // "القول الأول: ..." and "قال الله تعالى: ...": search for what follows the colon.
        const colon = line.indexOf(':');
        if (colon !== -1 && line.slice(0, colon).trim().split(/\s+/).length <= 3) {
            line = line.slice(colon + 1).trim();
        }
        const words = line.split(/\s+/).filter(Boolean);
        if (words.length >= 4) {
            return words.slice(0, WORDS).join(' ').replace(/[،؛:.]+$/, '');
        }
    }
    return '';
}

/** The page's address, extended to land on the passage when one can be pointed at. */
export function passageLink(url, text) {
    const lead = passageLead(text);
    if (!url || !lead || String(url).includes('#')) return url || '';
    return `${url}#:~:text=${encodeURIComponent(lead)}`;
}
