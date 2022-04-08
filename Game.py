#Tutorial credits
#https://arsthaumaturgis.github.io/Panda3DTutorial.io/tutorial/tut_lesson01.html

from direct.showbase.ShowBase import ShowBase

from direct.actor.Actor import Actor
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionSphere, CollisionTube, CollisionNode
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import Vec4, Vec3
from panda3d.core import WindowProperties
import random

from direct.gui.DirectGui import *
from GameObject import *

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        #Disable mouse
        self.disableMouse()

        #Set window properties
        properties = WindowProperties()
        properties.setSize(1000, 750)
        self.win.requestProperties(properties)

        #For exiting game and starting a new level
        self.exitFunc = self.cleanup        

        #Add ambient lighting
        ambientLight = AmbientLight("ambient light")
        ambientLight.setColor(Vec4(0.2, 0.2, 0.2, 1))
        self.ambientLightNodePath = render.attachNewNode(ambientLight)
        render.setLight(self.ambientLightNodePath)

        #Add directional light
        mainLight = DirectionalLight("main light")
        self.mainLightNodePath = render.attachNewNode(mainLight)
        # Turn it around by 45 degrees, and tilt it down by 45 degrees
        self.mainLightNodePath.setHpr(45, -45, 0)
        render.setLight(self.mainLightNodePath)

        #Add simple shader
        render.setShaderAuto()
        
        #Load environment
        self.environment = loader.loadModel("Models/Misc/environment")
        self.environment.reparentTo(render)
      
        # Move the camera to a position high above the screen
        # --that is, offset it along the z-axis.
        self.camera.setPos(0, 0, 32)
        # Tilt the camera down by setting its pitch.
        self.camera.setP(-90)

        #Set up key map
        self.keyMap = {
            "up" : False,
            "down" : False,
            "left" : False,
            "right" : False,
            "shoot" : False
        }
              
        self.accept("w", self.updateKeyMap, ["up", True])
        self.accept("w-up", self.updateKeyMap, ["up", False])
        self.accept("s", self.updateKeyMap, ["down", True])
        self.accept("s-up", self.updateKeyMap, ["down", False])
        self.accept("a", self.updateKeyMap, ["left", True])
        self.accept("a-up", self.updateKeyMap, ["left", False])
        self.accept("d", self.updateKeyMap, ["right", True])
        self.accept("d-up", self.updateKeyMap, ["right", False])
        self.accept("mouse1", self.updateKeyMap, ["shoot", True])
        self.accept("mouse1-up", self.updateKeyMap, ["shoot", False])
        
        #Collisions        
        self.pusher = CollisionHandlerPusher()
        self.cTrav = CollisionTraverser()
        
        #This accounts for 2d only collisons
        self.pusher.setHorizontal(True)

        #Pattern for the trap enemy to move along
        self.pusher.add_in_pattern("%fn-into-%in")
        self.accept("trapEnemy-into-wall", self.stopTrap)
        self.accept("trapEnemy-into-trapEnemy", self.stopTrap)
        self.accept("trapEnemy-into-player", self.trapHitsSomething)
        self.accept("trapEnemy-into-walkingEnemy", self.trapHitsSomething)


        # Tubes are defined by their start-points, end-points, and radius.
        # In this first case, the tube goes from (-8, 0, 0) to (8, 0, 0),
        # and has a radius of 0.2.

        #Adding walls
        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = render.attachNewNode(wallNode)
        wall.setY(8.0)

        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = render.attachNewNode(wallNode)
        wall.setY(-8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = render.attachNewNode(wallNode)
        wall.setX(8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = render.attachNewNode(wallNode)
        wall.setX(-8.0)


        self.updateTask = taskMgr.add(self.update, "update")
        
        self.player = None
        
       # Our enemies, traps, and "dead enemies"
        self.enemies = []
        self.trapEnemies = []

        self.deadEnemies = []

        # Set up some spawn points
        self.spawnPoints = []
        numPointsPerWall = 5
        for i in range(numPointsPerWall):
            coord = 7.0/numPointsPerWall + 0.5
            self.spawnPoints.append(Vec3(-7.0, coord, 0))
            self.spawnPoints.append(Vec3(7.0, coord, 0))
            self.spawnPoints.append(Vec3(coord, -7.0, 0))
            self.spawnPoints.append(Vec3(coord, 7.0, 0))

        # Values to control when to spawn enemies, and
        # how many enemies there may be at once
        self.initialSpawnInterval = 1.0
        self.minimumSpawnInterval = 0.2
        self.spawnInterval = self.initialSpawnInterval
        self.spawnTimer = self.spawnInterval
        self.maxEnemies = 2
        self.maximumMaxEnemies = 20

        self.numTrapsPerSide = 2

        self.difficultyInterval = 5.0
        self.difficultyTimer = self.difficultyInterval

        self.enemySpawnSound = loader.loadSfx("Sounds/enemySpawn.ogg")

        #Game Over screen
        self.gameOverScreen = DirectDialog(frameSize = (-0.7, 0.7, -0.7, 0.7),
                                           fadeScreen = 0.4,
                                           relief = DGG.FLAT,
                                           frameTexture = "UI/stoneFrame.png")
        self.gameOverScreen.hide()

        self.font = loader.loadFont("Fonts/Wbxkomik.ttf")

        buttonImages = (
            loader.loadTexture("UI/UIButton.png"),
            loader.loadTexture("UI/UIButtonPressed.png"),
            loader.loadTexture("UI/UIButtonHighlighted.png"),
            loader.loadTexture("UI/UIButtonDisabled.png")
        )

        label = DirectLabel(text = "Game Over!",
                            parent = self.gameOverScreen,
                            scale = 0.1,
                            pos = (0, 0, 0.2),
                            text_font = self.font,
                            relief = None)
        
        self.finalScoreLabel = DirectLabel(text = "",
                                           parent = self.gameOverScreen,
                                           scale = 0.07,
                                           pos = (0, 0, 0),
                                           text_font = self.font,
                                           relief = None)

        btn = DirectButton(text = "Restart",
                           command = self.startGame,
                           pos = (-0.3, 0, -0.2),
                           parent = self.gameOverScreen,
                           scale = 0.07,
                           text_font = self.font,
                           clickSound = loader.loadSfx("Sounds/UIClick.ogg"),
                           frameTexture = buttonImages,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)


        btn = DirectButton(text = "Quit",
                           command = self.quit,
                           pos = (0.3, 0, -0.2),
                           parent = self.gameOverScreen,
                           scale = 0.07,
                           text_font = self.font,
                           clickSound = loader.loadSfx("Sounds/UIClick.ogg"),
                           frameTexture = buttonImages,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        self.titleMenuBackdrop = DirectFrame(frameColor = (0, 0, 0, 1),
                                             frameSize = (-1, 1, -1, 1),
                                             parent = render2d)

        self.titleMenu = DirectFrame(frameColor = (1, 1, 1, 0))

        title = DirectLabel(text = "Panda-chan",
                            scale = 0.1,
                            pos = (0, 0, 0.9),
                            parent = self.titleMenu,
                            relief = None,
                            text_font = self.font,
                            text_fg = (1, 1, 1, 1))
        title2 = DirectLabel(text = "and the",
                             scale = 0.07,
                             pos = (0, 0, 0.79),
                             parent = self.titleMenu,
                             text_font = self.font,
                             frameColor = (0.5, 0.5, 0.5, 1))
        title3 = DirectLabel(text = "Endless Horde",
                             scale = 0.125,
                             pos = (0, 0, 0.65),
                             parent = self.titleMenu,
                             relief = None,
                             text_font = self.font,
                             text_fg = (1, 1, 1, 1))

        btn = DirectButton(text = "Start Game",
                           command = self.startGame,
                           pos = (0, 0, 0.2),
                           parent = self.titleMenu,
                           scale = 0.1,
                           text_font = self.font,
                           clickSound = loader.loadSfx("Sounds/UIClick.ogg"),
                           frameTexture = buttonImages,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        btn = DirectButton(text = "Quit",
                           command = self.quit,
                           pos = (0, 0, -0.2),
                           parent = self.titleMenu,
                           scale = 0.1,
                           text_font = self.font,
                           clickSound = loader.loadSfx("Sounds/UIClick.ogg"),
                           frameTexture = buttonImages,
                           frameSize = (-4, 4, -1, 1),
                           text_scale = 0.75,
                           relief = DGG.FLAT,
                           text_pos = (0, -0.2))
        btn.setTransparency(True)

        #Music
        music = loader.loadMusic("Music/Defending-the-Princess-Haunted.ogg")
        music.setLoop(True)
        music.setVolume(0.075)
        music.play()

    def startGame(self):
        self.titleMenu.hide()
        self.titleMenuBackdrop.hide()
        self.gameOverScreen.hide()

        self.cleanup()

        self.player = Player()

        self.maxEnemies = 2
        self.spawnInterval = self.initialSpawnInterval

        self.difficultyTimer = self.difficultyInterval

        sideTrapSlots = [
            [],
            [],
            [],
            []
        ]
        trapSlotDistance = 0.4
        slotPos = -8 + trapSlotDistance
        while slotPos < 8:
            if abs(slotPos) > 1.0:
                sideTrapSlots[0].append(slotPos)
                sideTrapSlots[1].append(slotPos)
                sideTrapSlots[2].append(slotPos)
                sideTrapSlots[3].append(slotPos)
            slotPos += trapSlotDistance

        # Create one trap on each side, repeating
        # for however many traps there should be
        # per side.
        for i in range(self.numTrapsPerSide):
            # Note that we "pop" the chosen location,
            # so that it won't be chosen again.
            slot = sideTrapSlots[0].pop(random.randint(0, len(sideTrapSlots[0])-1))
            trap = TrapEnemy(Vec3(slot, 7.0, 0))
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[1].pop(random.randint(0, len(sideTrapSlots[1])-1))
            trap = TrapEnemy(Vec3(slot, -7.0, 0))
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[2].pop(random.randint(0, len(sideTrapSlots[2])-1))
            trap = TrapEnemy(Vec3(7.0, slot, 0))
            trap.moveInX = True
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[3].pop(random.randint(0, len(sideTrapSlots[3])-1))
            trap = TrapEnemy(Vec3(-7.0, slot, 0))
            trap.moveInX = True
            self.trapEnemies.append(trap)

    def updateKeyMap(self, controlName, controlState):
            self.keyMap[controlName] = controlState

    def spawnEnemy(self):
        if len(self.enemies) < self.maxEnemies:
            spawnPoint = random.choice(self.spawnPoints)

            newEnemy = WalkingEnemy(spawnPoint)

            self.enemies.append(newEnemy)

            self.enemySpawnSound.play()

    def stopTrap(self, entry):
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")
            trap.moveDirection = 0
            trap.ignorePlayer = False
            trap.movementSound.stop()
            trap.stopSound.play()

    def trapHitsSomething(self, entry):
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")
            # We don't want stationary traps to do damage,
            # so ignore the collision if the "moveDirection" is 0
            if trap.moveDirection == 0:
                return

            collider = entry.getIntoNodePath()
            if collider.hasPythonTag("owner"):
                obj = collider.getPythonTag("owner")
                if isinstance(obj, Player):
                    if not trap.ignorePlayer:
                        obj.alterHealth(-1)
                        trap.ignorePlayer = True
                else:
                    obj.alterHealth(-10)

                trap.impactSound.play()

    def update(self, task):
        dt = globalClock.getDt()

        # If the player is dead, or we're not
        # playing yet, ignore this logic.
        if self.player is not None:
            if self.player.health > 0:
                self.player.update(self.keyMap, dt)

                # Wait to spawn an enemy...
                self.spawnTimer -= dt
                if self.spawnTimer <= 0:
                    # Spawn one!
                    self.spawnTimer = self.spawnInterval
                    self.spawnEnemy()

                # Update all enemies and traps
                [enemy.update(self.player, dt) for enemy in self.enemies]
                [trap.update(self.player, dt) for trap in self.trapEnemies]

                # Find the enemies that have just
                # died, if any
                newlyDeadEnemies = [enemy for enemy in self.enemies if enemy.health <= 0]
                # And re-build the enemy-list to exclude
                # those that have just died.
                self.enemies = [enemy for enemy in self.enemies if enemy.health > 0]

                # Newly-dead enemies should have no collider,
                # and should play their "die" animation.
                # In addition, increase the player's score.
                for enemy in newlyDeadEnemies:
                    enemy.collider.removeNode()
                    enemy.actor.play("die")
                    self.player.score += enemy.scoreValue
                if len(newlyDeadEnemies) > 0:
                    self.player.updateScore()

                self.deadEnemies += newlyDeadEnemies

                # Check our "dead enemies" to see
                # whether they're still animating their
                # "die" animation. In not, clean them up,
                # and drop them from the "dead enemies" list.
                enemiesAnimatingDeaths = []
                for enemy in self.deadEnemies:
                    deathAnimControl = enemy.actor.getAnimControl("die")
                    if deathAnimControl is None or not deathAnimControl.isPlaying():
                        enemy.cleanup()
                    else:
                        enemiesAnimatingDeaths.append(enemy)
                self.deadEnemies = enemiesAnimatingDeaths

                # Make the game more difficult over time!
                self.difficultyTimer -= dt
                if self.difficultyTimer <= 0:
                    self.difficultyTimer = self.difficultyInterval
                    if self.maxEnemies < self.maximumMaxEnemies:
                        self.maxEnemies += 1
                    if self.spawnInterval > self.minimumSpawnInterval:
                        self.spawnInterval -= 0.1
            else:
                if self.gameOverScreen.isHidden():
                    self.gameOverScreen.show()
                    self.finalScoreLabel["text"] = "Final score: " + str(self.player.score)
                    self.finalScoreLabel.setText()


        return task.cont

    def cleanup(self):
        # Call our various cleanup methods,
        # empty the various lists,
        # and make the player "None" again.

        for enemy in self.enemies:
            enemy.cleanup()
        self.enemies = []

        for enemy in self.deadEnemies:
            enemy.cleanup()
        self.deadEnemies = []

        for trap in self.trapEnemies:
            trap.cleanup()
        self.trapEnemies = []

        if self.player is not None:
            self.player.cleanup()
            self.player = None

    def quit(self):
        # Clean up, then exit

        self.cleanup()

        base.userExit()


game = Game()
game.run()

