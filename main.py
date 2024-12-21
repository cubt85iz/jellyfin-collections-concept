import json
import os

from jellyfin_api_client import AuthenticatedClient
from jellyfin_api_client.api.collection import add_to_collection, create_collection, remove_from_collection
from jellyfin_api_client.api.items import get_items
from jellyfin_api_client.api.item_update import update_item
from jellyfin_api_client.models import ItemFields, BaseItemKind, BaseItemDto

JELLYFIN_ENDPOINT = os.environ["JELLYFIN_ENDPOINT"]
JELLYFIN_TOKEN = os.environ["JELLYFIN_TOKEN"]

# Load collections from configuration file
if os.path.exists('config.json'):
  with open('config.json', 'r') as config_json:
    config = json.load(config_json)

# Create client for Jellyfin
jellyfin_client = AuthenticatedClient(
  base_url=JELLYFIN_ENDPOINT,
  token=f'Token={JELLYFIN_TOKEN}',
  prefix="MediaBrowser",
)

# Gather existing collections from Jellyfin
jellyfin_collections = get_items.sync(
  client=jellyfin_client,
  include_item_types=[BaseItemKind.BOXSET],
  recursive=True
).items

# Gather existing movies from Jellyfin
jellyfin_movies = get_items.sync(
  client=jellyfin_client,
  include_item_types=[BaseItemKind.MOVIE],
  fields=[ItemFields.PROVIDERIDS],
  recursive=True
).items

# Iterate through collections in configuration and build a mapping of matches
for collection in config['collections']:

  # Initialize the connection map to define order.
  collection_map = {}
  for identifier in collection['identifiers']:
    collection_map[identifier] = []

  # Iterate through movies and add any missing movies to the map
  for movie in jellyfin_movies:
    if 'Imdb' in movie.provider_ids.additional_properties:
      imdb_id = movie.provider_ids.additional_properties['Imdb']
      if imdb_id in collection['identifiers']:
        if movie.id not in collection_map[imdb_id]:
          collection_map[imdb_id].append(movie.id)

  # Build list of movie identifiers for collection
  jellyfin_movie_ids=[]
  for key, value in collection_map.items():
    jellyfin_movie_ids += value

  jellyfin_collection_id = next((c.id for c in jellyfin_collections if c.name == collection['name']), "")
  if jellyfin_collection_id:
    # If collection exists, remove the current items and
    # add the movies detected during this execution. This
    # behavior is in response to how the "Default" sort works.
    # When "Date Modified" display order is selected, items are
    # sorted by when they're added.
    response = remove_from_collection.sync_detailed(
      client=jellyfin_client,
      collection_id=jellyfin_collection_id,
      ids=jellyfin_movie_ids
    )

    response = add_to_collection.sync_detailed(
      client=jellyfin_client,
      collection_id=jellyfin_collection_id,
      ids=jellyfin_movie_ids
    )
  else:
    # If collection doesn't exist create it using the movies
    # detected during this execution.
    response = create_collection.sync_detailed(
      client=jellyfin_client,
      name = collection['name'],
      ids=jellyfin_movie_ids
    )
