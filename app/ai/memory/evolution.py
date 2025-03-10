"""
Memory evolution system for knowledge base connections
"""
from typing import List, Dict, Tuple
import datetime
import json
from bson.objectid import ObjectId
from app.config.config import logger, EVOLUTION_THRESHOLD

class MemoryEvolutionSystem:
    """System for evolving knowledge base connections over time"""
    
    def __init__(self, 
                 db, 
                 llm_controller=None, 
                 embedding_retriever=None, 
                 evolution_threshold: int = EVOLUTION_THRESHOLD):
        """Initialize the memory evolution system
        
        Args:
            db: MongoDB database connection
            llm_controller: LLM controller for analyzing content
            embedding_retriever: Embedding retriever for semantic search
            evolution_threshold: Number of note additions before triggering consolidation
        """
        self.db = db
        self.notes_collection = db['notes']
        self.llm_controller = llm_controller
        self.embedding_retriever = embedding_retriever
        self.evolution_counter = 0
        self.evolution_threshold = evolution_threshold
        
    def process_new_note(self, note_id: str) -> None:
        """Process a new note and update connections
        
        Args:
            note_id: ID of the new note
        """
        # Increment evolution counter
        self.evolution_counter += 1
        
        # Skip if we don't have AI capabilities
        if not self.llm_controller or not self.embedding_retriever:
            return
            
        try:
            # Get the note
            note = self.notes_collection.find_one({"_id": ObjectId(note_id)})
            if not note:
                logger.error(f"Note not found: {note_id}")
                return
                
            # Find related notes
            related_notes = self._find_related_notes(note)
            if not related_notes:
                logger.info(f"No related notes found for note: {note_id}")
                return
                
            # Get evolution suggestions
            suggestions = self._get_evolution_suggestions(note, related_notes)
            
            # Apply suggestions
            self._apply_evolution_suggestions(note, related_notes, suggestions)
            
            # Check if we should consolidate
            if self.evolution_counter >= self.evolution_threshold:
                self.consolidate_knowledge_base()
                self.evolution_counter = 0
                
        except Exception as e:
            logger.error(f"Error in process_new_note: {str(e)}")
    
    def _find_related_notes(self, note: Dict) -> List[Dict]:
        """Find notes related to the given note"""
        if not self.embedding_retriever or not note:
            return []
            
        try:
            # Get content with metadata for better matching
            content = note.get('content', '')
            title = note.get('title', '')
            keywords = ' '.join(note.get('keywords', []))
            tags = ' '.join(note.get('tags', []))
            
            query = f"{title} {content} {keywords} {tags}"
            
            # Search for related notes
            search_results = self.embedding_retriever.search(query, k=5)
            
            # Get notes from database
            related_notes = []
            for doc_id, _ in search_results:
                # Skip if it's the same note
                if str(note['_id']) == doc_id:
                    continue
                    
                try:
                    related_note = self.notes_collection.find_one({"_id": ObjectId(doc_id)})
                    if related_note:
                        related_notes.append(related_note)
                except:
                    continue
                    
            return related_notes
        except Exception as e:
            logger.error(f"Error finding related notes: {str(e)}")
            return []
    
    def _get_evolution_suggestions(self, note: Dict, related_notes: List[Dict]) -> Dict:
        """Get suggestions for evolving the knowledge base"""
        if not self.llm_controller:
            return {}
            
        try:
            # Format note data
            note_data = {
                "id": str(note["_id"]),
                "title": note.get("title", ""),
                "content": note.get("content", ""),
                "context": note.get("context", ""),
                "keywords": note.get("keywords", []),
                "tags": note.get("tags", [])
            }
            
            # Format related notes data
            related_notes_data = []
            for i, rel_note in enumerate(related_notes):
                related_notes_data.append({
                    "index": i,
                    "id": str(rel_note["_id"]),
                    "title": rel_note.get("title", ""),
                    "content": rel_note.get("content", ""),
                    "context": rel_note.get("context", ""),
                    "keywords": rel_note.get("keywords", []),
                    "tags": rel_note.get("tags", [])
                })
                
            # Create prompt for LLM
            prompt = f"""Analyze the relationships between a new note and existing related notes in a knowledge base.
            
            New Note:
            Title: {note_data['title']}
            Content: {note_data['content']}
            Context: {note_data['context']}
            Keywords: {', '.join(note_data['keywords'])}
            Tags: {', '.join(note_data['tags'])}
            
            Related Notes:
            {json.dumps(related_notes_data, indent=2)}
            
            Please provide suggestions for evolving the knowledge base:
            1. Identify bidirectional links that should be created
            2. Suggest tags that should be added to related notes
            3. Suggest updates to the context of related notes
            
            Return your suggestions as JSON:
            {{
                "bidirectional_links": [
                    {{
                        "note_id": "related_note_id",
                        "index": 0, // Index from the related notes list
                        "link_reason": "These notes are closely related because..."
                    }}
                ],
                "tag_suggestions": [
                    {{
                        "note_id": "related_note_id",
                        "index": 0,
                        "tags_to_add": ["tag1", "tag2"]
                    }}
                ],
                "context_updates": [
                    {{
                        "note_id": "related_note_id",
                        "index": 0,
                        "new_context": "Updated context description"
                    }}
                ]
            }}
            """
            
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "bidirectional_links": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "note_id": {"type": "string"},
                                        "index": {"type": "integer"},
                                        "link_reason": {"type": "string"}
                                    }
                                }
                            },
                            "tag_suggestions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "note_id": {"type": "string"},
                                        "index": {"type": "integer"},
                                        "tags_to_add": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            },
                            "context_updates": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "note_id": {"type": "string"},
                                        "index": {"type": "integer"},
                                        "new_context": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # Get suggestions from LLM
            response = self.llm_controller.llm.get_completion(prompt, response_format)
            
            try:
                suggestions = json.loads(response)
                return suggestions
            except json.JSONDecodeError:
                logger.error(f"Error parsing evolution suggestions: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting evolution suggestions: {str(e)}")
            return {}
    
    def _apply_evolution_suggestions(self, note: Dict, related_notes: List[Dict], suggestions: Dict) -> None:
        """Apply evolution suggestions to the knowledge base"""
        try:
            current_note_id = str(note["_id"])
            current_note_title = note.get("title", "")
            
            # Apply bidirectional links
            for link_suggestion in suggestions.get("bidirectional_links", []):
                idx = link_suggestion.get("index")
                if 0 <= idx < len(related_notes):
                    related_note = related_notes[idx]
                    related_note_id = related_note["_id"]
                    related_note_title = related_note.get("title", "")
                    
                    # Add link to current note (if not already linked)
                    if related_note_title not in note.get("links", []):
                        self.notes_collection.update_one(
                            {"_id": ObjectId(current_note_id)},
                            {"$addToSet": {"links": related_note_title}}
                        )
                    
                    # Add reverse link to related note
                    self.notes_collection.update_one(
                        {"_id": related_note_id},
                        {"$addToSet": {"links": current_note_title}}
                    )
                    
                    logger.info(f"Created bidirectional link between notes {current_note_id} and {related_note_id}")
            
            # Apply tag suggestions
            for tag_suggestion in suggestions.get("tag_suggestions", []):
                idx = tag_suggestion.get("index")
                if 0 <= idx < len(related_notes):
                    related_note = related_notes[idx]
                    related_note_id = related_note["_id"]
                    tags_to_add = tag_suggestion.get("tags_to_add", [])
                    
                    if tags_to_add:
                        # Update note tags
                        self.notes_collection.update_one(
                            {"_id": related_note_id},
                            {"$addToSet": {"tags": {"$each": tags_to_add}}}
                        )
                        
                        # Update tags collection
                        for tag in tags_to_add:
                            self.db['tags'].update_one(
                                {'name': tag},
                                {'$set': {'name': tag}, '$addToSet': {'note_ids': related_note_id}},
                                upsert=True
                            )
                        
                        logger.info(f"Added tags {tags_to_add} to note {related_note_id}")
            
            # Apply context updates
            for context_update in suggestions.get("context_updates", []):
                idx = context_update.get("index")
                if 0 <= idx < len(related_notes):
                    related_note = related_notes[idx]
                    related_note_id = related_note["_id"]
                    new_context = context_update.get("new_context")
                    
                    if new_context:
                        # Update note context
                        self.notes_collection.update_one(
                            {"_id": related_note_id},
                            {"$set": {"context": new_context}}
                        )
                        
                        logger.info(f"Updated context of note {related_note_id} to '{new_context}'")
                        
        except Exception as e:
            logger.error(f"Error applying evolution suggestions: {str(e)}")
    
    def consolidate_knowledge_base(self) -> None:
        """Consolidate the knowledge base by updating embeddings"""
        if not self.embedding_retriever:
            return
            
        try:
            # Reset the embedding retriever
            self.embedding_retriever.reset()
            
            # Get all notes
            notes = self.notes_collection.find()
            
            # Prepare documents for embedding
            documents = []
            doc_ids = []
            
            for note in notes:
                # Combine content with metadata for better search
                title = note.get('title', '')
                content = note.get('content', '')
                keywords = ' '.join(note.get('keywords', []))
                context = note.get('context', '')
                tags = ' '.join(note.get('tags', []))
                
                document = f"{title} {content} {keywords} {context} {tags}"
                documents.append(document)
                doc_ids.append(str(note['_id']))
            
            # Update embeddings
            if documents:
                self.embedding_retriever.add_documents(documents, doc_ids)
                
            logger.info(f"Knowledge base consolidated with {len(documents)} notes")
            
        except Exception as e:
            logger.error(f"Error consolidating knowledge base: {str(e)}")