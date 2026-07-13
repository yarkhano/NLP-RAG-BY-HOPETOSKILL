import uvicorn
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from uuid import uuid4
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from storage import StoreNotes


app = FastAPI(
    title = "Notes App",
    description  = "This is a basic notes api app.",
    version = "1.0.0.0"
)


# Allow your React frontend to communicate with the FastAPI backend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AddNote(BaseModel):
     note: str


class ResponseModel(BaseModel):
    noteID: str
    note: str


@app.post("/notes",response_model=ResponseModel)
async def create_note(addnote:AddNote):
     notes_id = uuid4()
     coming_note = addnote.note
     response = {"noteID": str(notes_id), "note": coming_note}
     StoreNotes[str(notes_id)] = coming_note
     return response


@app.get("/notes",response_model=List[ResponseModel])
async def get_notes():
    noteslist = []
    for note_id,note in StoreNotes.items():
        n_res = ResponseModel(
            noteID=str(note_id),
            note=note
        )
        noteslist.append(n_res)
    return noteslist


@app.put("/notes/{noteID}")
async def update_note(noteID:str,addnote:AddNote):
    if noteID in StoreNotes:
        new_note = addnote.note
        StoreNotes[noteID] = new_note
        rep = {"noteID": str(noteID), "note": new_note}
        return rep

    else:
        raise HTTPException(status_code=404, detail="Note not found")



@app.delete("/notes/{noteID}")
async def delete_note(noteID:str):
    if noteID in StoreNotes:
        del StoreNotes[noteID]
        return {"message": "Note deleted"}
    else:
        raise HTTPException(status_code=404, detail="Note not found")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)