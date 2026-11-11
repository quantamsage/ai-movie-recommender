"""A small in-session watchlist. Pure Python so it's easy to test."""

import csv
import io

CSV_FIELDS = ["title", "year", "genre", "match_score", "description", "why_recommended"]


def movie_key(movie):
    """Identify a movie by title and year, ignoring case."""
    return (movie["title"].casefold(), movie["year"])


def contains(watchlist, movie):
    return any(movie_key(saved) == movie_key(movie) for saved in watchlist)


def add(watchlist, movie):
    """Return a new watchlist with `movie` added, unless it's already there."""
    if contains(watchlist, movie):
        return list(watchlist)
    return [*watchlist, dict(movie)]


def remove(watchlist, movie):
    """Return a new watchlist without `movie`."""
    return [saved for saved in watchlist if movie_key(saved) != movie_key(movie)]


def to_csv(watchlist):
    """Export the watchlist as CSV text."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(watchlist)
    return buffer.getvalue()
