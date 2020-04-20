from flask import Flask, render_template
from flask import jsonify
from flask import request, abort
from flask import Response 
import dataif as DataIf
from base import Game, Player
from config import serverconfig, getGameInfo

BASEURI="/gamelobby/v1"
 
# Expose these routes to the main server application 
from flask import Blueprint
lobbyrest_blueprint = Blueprint('lobbyrest_blueprint', __name__)

# GET / Confirm Server is running
# TODO: return lobby REST endpoints
@lobbyrest_blueprint.route(BASEURI + '/', methods=['GET'])
def rest_lobby_hello():
    return jsonify({'message' : 'Hello, World!'})
 
# get /gametypes list of existing types of games on the server
@lobbyrest_blueprint.route(BASEURI + '/gametypes', methods=['get'])
def rest_lobby_get_gametypes():
  return jsonify({'gametypes' : [{'name': game['name'], 'url': game['starturl']} for game in serverconfig['games']]})
  
# GET /games List of existing games on the server
@lobbyrest_blueprint.route(BASEURI + '/games', methods=['GET'])
def rest_lobby_get_games():
  return jsonify({'games' : DataIf.getAllGameIds()})

# POST /games Create a new game
@lobbyrest_blueprint.route(BASEURI + '/games', methods=['POST'])
def rest_lobby_make_game():
  if not request.json or not 'gamename' in request.json:
    print("didn't specify the game type to create")
    abort(404)
   
  req_gname=request.json['gamename']
  if getGameInfo(req_gname) is None:
    print("asking for a game that doesn't exist")
    abort(404)
     
  newGame=DataIf.createGame(req_gname)
  if newGame:
    return Response(request.base_url + '/' + str(newGame.id), status=201)
  else:
    abort(404) # couldn't create the game
   
# GET /games/id Get details about a specific game
@lobbyrest_blueprint.route(BASEURI + '/games/<int:gameid>', methods=['GET'])
def rest_lobby_get_game_info(gameid):
  req_game=DataIf.getGameById(gameid)
  if req_game is not None:
    return jsonify({'game' : req_game.serialize(req_game)})
  else:
    abort(404) #no such game
   
# PATCH /games/id Start or Stop a specific game
@lobbyrest_blueprint.route(BASEURI + '/games/<int:gameid>', methods=['PATCH'])
def rest_lobby_start_game(gameid):
  # make sure they're trying to set running : true
  print(request.json)
  if not request.json or not 'started' in request.json:
    print("no json, or not asking to update the 'started' field")
    abort(400)
  
  # Find the game they want to run
  req_game=DataIf.getGameById(gameid)
  if req_game is None:
    print("some dummy just tried to twiddle with a non existent game")
    abort(400)

  # Find out if they want to stop a game
  if request.json['started'] == 'false':
    if not req_game.started:
      abort(400) # game is not started, can't stop it
    req_game.stop()
    return jsonify({'success':True})
    
  # Or start one
  elif request.json['started'] == 'true':
    # make sure there are enough players
    num_players, players=req_game.players
    if num_players < req_game.minPlayers() or num_players > req_game.maxPlayers():
      print("Not enough players to play yet")
      abort(400)
       
    # if we got this far, they must have asked us to start the game
    req_game.run() # note, probably won't do anything
     
    # return the URL for the running game (maybe tilebag/<id>?)
    # TODO: We might want a different url pattern, with version?
    return Response(request.host_url[:-1] + req_game.starturl() + '/' + str(gameid), status=201)
  # Or if they were on glue
  else:
    print("some keener tried to change started to something other than true")
    abort(400)
   
  abort(404) # Couldn't find the game
   
# GET /games/<id>/players List all the players playing a specific game
@lobbyrest_blueprint.route(BASEURI + '/games/<int:gameid>/players', methods=['GET'])
def rest_lobby_get_players(gameid): 
  players=DataIf.getAllPlayersInGame(gameid)
  if players is not None:
    return jsonify({'players' : [player.serialize() for player in players]})
  else:
    abort(404) #Likely no such game
     
# GET /games/<id>/players/<id> Get specific details about a given player
@lobbyrest_blueprint.route(BASEURI + '/games/<int:gameid>/players/<int:playerid>', methods=['GET'])
def rest_lobby_get_player_info(gameid, playerid): 
  players=DataIf.getAllPlayersInGame(gameid)
  if players is not None:
    for player in players:
      if player.id == playerid:
        return jsonify({'player' : player.serialize()})
    abort(404) #no such player
  else:
    abort(404) #Likely no such game
     
# POST /games/id/players - Join the game
# TODO: get the USER info from the logged in person, not the post data
@lobbyrest_blueprint.route(BASEURI + '/games/<int:gameid>/players', methods=['POST'])
def rest_lobby_join_game(gameid):
  # Get the user that wants to the join the game
  print(request.json)
  if not request.json or not 'name' in request.json:
    print("something wrong with the json")
    abort(400)
  newPlayerName=request.json['name']

  # Find the game they want to join
  req_game=DataIf.getGameById(gameid)
  if req_game is not None:
    # make sure there's room for one more at the table
    num_players, players=req_game.players
    if num_players >= req_game.maxPlayers():
      print("whoa-la, already at the max for players")
      abort(400)
     
    print("cool cool, try to add this player to the game!")
    newPlayerId=(gameid<<8)+(num_players+1)
    print("newPlayerId == " + str(newPlayerId))
    if req_game.addPlayer(req_game.newPlayer(newPlayerId,newPlayerName)):
      DataIf.updateGame(gameid)
      return Response(request.base_url + '/' + str(newPlayerId), status=201)
    else:
      abort(401) #that's odd
  else:
    abort(404) #no such game
