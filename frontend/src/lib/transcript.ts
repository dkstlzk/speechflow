export function formatTranscriptTime(
    sec?: number
) {
    if (sec === undefined || sec === null) {
        return "--:--";
    }

    const minutes = Math.floor(sec / 60);
    const seconds = Math.floor(sec % 60);

    return `${minutes
        .toString()
        .padStart(2, "0")}:${seconds
            .toString()
            .padStart(2, "0")}`;
}