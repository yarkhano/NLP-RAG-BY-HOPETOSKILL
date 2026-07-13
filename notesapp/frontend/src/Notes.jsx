import { useState, useEffect } from "react";

export default function Notes() {
    const [noteText, setNoteText] = useState("");
    const [notesList, setNotesList] = useState([]);

    // Fetch notes from your FastAPI backend
    async function fetchNotes() {
        try {
            const response = await fetch("http://127.0.0.1:8000/notes");
            const data = await response.json();
            setNotesList(data);
        } catch (error) {
            console.error("Failed to fetch notes from backend:", error);
        }
    }

    // Load notes when the app page opens
    useEffect(() => {
        fetchNotes();
    }, []);

    async function addNote() {
        if (!noteText.trim()) return;

        try {
            const response = await fetch("http://127.0.0.1:8000/notes", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    note: noteText
                })
            });

            const data = await response.json();
            console.log("Server response:", data);

            setNoteText(""); // Reset input field
            fetchNotes();    // Refresh list view instantly
        } catch (error) {
            console.error("Failed to connect to backend:", error);
        }
    }

    return (
        <div style={{ padding: "40px", maxWidth: "600px", margin: "0 auto", textAlign: "left" }}>
            <h2>My RAG Notes App</h2>

            <div style={{ marginBottom: "20px" }}>
                <input
                    type="text"
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Type a note..."
                    style={{ marginRight: "10px", padding: "8px", width: "70%" }}
                />
                <button onClick={addNote} style={{ padding: "8px 16px" }}>Add Note</button>
            </div>

            <h3>Saved Notes:</h3>
            {notesList.length === 0 ? (
                <p style={{ color: "var(--text)" }}>No notes found. Create one above!</p>
            ) : (
                <ul>
                    {notesList.map((n) => (
                        <li key={n.noteID} style={{ margin: "10px 0", color: "var(--text)" }}>
                            {n.note}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}