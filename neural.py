import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import cross_val_score

class SwearWordClassifier:
    def __init__(self):
        with open('swears.txt', 'r', encoding='utf-8') as f:
            self.swear_words = [word.strip() for word in f.readlines()]

        comments_df = pd.read_csv('comments.csv', usecols=['comments', 'is_swear_word'])
        comments = comments_df['comments'].astype(str)

        self.vectorizer = TfidfVectorizer()
        X = self.vectorizer.fit_transform(comments)

        y = comments_df['is_swear_word']

        self.model = MLPClassifier(hidden_layer_sizes=(500), 
                                   alpha=0.5, 
                                   max_iter=3000, 
                                   early_stopping=True, 
                                   solver='lbfgs')

        # Perform cross-validation
        scores = cross_val_score(self.model, X, y, cv=2, scoring='accuracy')
        print(f'Cross-validation scores: {scores}')
        print(f'Average cross-validation score: {scores.mean()}')

        self.model.fit(X, y)

    def detect(self, word):
        prediction_proba = self.model.predict_proba(self.vectorizer.transform([word]))
        threshold = 0.6
        return (prediction_proba[0][1] >= threshold) or word in self.swear_words

print('Loading swear word classifier...')
classifier = SwearWordClassifier()

# while True:
#     print(classifier.detect(input('>')))