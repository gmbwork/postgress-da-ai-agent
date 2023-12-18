from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel

class DatabaseEmbeder:
    def __init__(self) -> None:
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.model = BertModel.from_pretrained('bert-base-uncased')
        self.map_name_to_embedding = {}
        self.map_name_to_tabel_def = {}
        
    def add_tabel(self, table_name: str, text_representation: str):
        self.map_name_to_tabel_def[table_name] = self.compute_embedding(
            text_representation
        )
        self.map_name_to_tabel_def[table_name] = text_representation
        
    def compute_embedding(self, text: str):
        inputs = self.tokenizer(
            text, 
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512,
        )
        outputs = self.model(**inputs)
        return outputs["pooler_output"].detach().numpy()
    
    def get_similar_tables_via_embeddings(self, query, n=3):
        """
        Given a query, find top n tables that are similar to the query
        
        Args:
        - query (str): The user's natural language query.
        - n (int, optional): The number of tables to return. Default value is 3.
        
        Returns:
        - list: Top `n` tables that are similar to the query.
        """
        # Compute the embedding of the query
        query_embedding = self.compute_embedding(query)
        # Calculate cosine similarity between the query and all tables
        similarities = {
            table: cosine_similarity(
                query_embedding, emb
            )[0][0]
            for table, emb in self.map_name_to_embedding.items()
        }
        # Rank tables based on their similarity score and return top n tables
        return sorted(similarities, key=similarities.get, reverse=True)[:n]
    
    
    def similarity_table_names_via_word_match(self, query: str):
        """
        If any word in the query is a table name, then add the table to a list
        """
        
        tables = []
        
        for table_name in self.map_name_to_tabel_def.keys():
            if table_name.lower() in query.lower():
                tables.append(table_name)
        
        return tables
    
    def get_similar_tables(self, query: str, n=3):
        """
        Combine results from `get_similar_tables_via_embeddings` and `similarity_table_names_via_word_match`
        """
        
        similar_tables_via_embeddings = self.get_similar_tables_via_embeddings(query, n)
        similar_tables_via_word_match = self.similarity_table_names_via_word_match(query)
        
        return list(set(similar_tables_via_embeddings + similar_tables_via_word_match))
    
    def get_table_definitions_from_names(self, table_names: list) -> list:
        """
        Given a list of table names, return their definitions
        """
        table_defs = [
            self.map_name_to_tabel_def[table_name] for table_name in table_names
        ]
        return "\n\n".join(table_defs)
    