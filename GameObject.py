
from panda3d.core import Vec4, Vec3, Vec2, Plane, Point3, BitMask32
from direct.actor.Actor import Actor
from panda3d.core import CollisionSphere, CollisionNode, CollisionRay, CollisionSegment, CollisionHandlerQueue
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode
from panda3d.core import AudioSound
from panda3d.core import PointLight

import math, random

FRICTION = 150.0


class GameObject():
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(render)
        self.actor.setPos(pos)

        self.maxHealth = maxHealth
        self.health = maxHealth

        self.maxSpeed = maxSpeed

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

        self.walking = False

        colliderNode = CollisionNode(colliderName)
        colliderNode.addSolid(CollisionSphere(0, 0, 0, 0.3))
        self.collider = self.actor.attachNewNode(colliderNode)
        self.collider.setPythonTag("owner", self)

        self.deathSound = None

    def update(self, dt):
        # If we're going faster than our maximum speed,
        # set the velocity-vector's length to that maximum
        speed = self.velocity.length()
        if speed > self.maxSpeed:
            self.velocity.normalize()
            self.velocity *= self.maxSpeed
            speed = self.maxSpeed

        # If we're walking, don't worry about friction.
        # Otherwise, use friction to slow us down.
        if not self.walking:
            frictionVal = FRICTION*dt
            if frictionVal > speed:
                self.velocity.set(0, 0, 0)
            else:
                frictionVec = -self.velocity
                frictionVec.normalize()
                frictionVec *= frictionVal

                self.velocity += frictionVec

        # Move the character, using our velocity and
        # the time since the last update.
        self.actor.setPos(self.actor.getPos() + self.velocity*dt)

    def alterHealth(self, dHealth):
        previousHealth = self.health
        self.health += dHealth

        if self.health > self.maxHealth:
            self.health = self.maxHealth
        if previousHealth > 0 and self.health <= 0 and self.deathSound is not None:
            self.deathSound.play()

    def cleanup(self):
        # Remove various nodes, and clear the Python-tag--see below!

        if self.collider is not None and not self.collider.isEmpty():
            self.collider.clearPythonTag("owner")
            base.cTrav.removeCollider(self.collider)
            base.pusher.removeCollider(self.collider)

        if self.actor is not None:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        self.collider = None

class Player(GameObject):
    def __init__(self):
        GameObject.__init__(self,
                            Vec3(0, 0, 0),
                            "Models/PandaChan/act_p3d_chan",
                              {
                                  "stand" : "Models/PandaChan/a_p3d_chan_idle",
                                  "walk" : "Models/PandaChan/a_p3d_chan_run"
                              },
                            5,
                            10,
                            "player")

        # Panda-chan faces "backwards", so we just turn
        # the first sub-node of our Actor-NodePath
        # to have it face as we want.
        self.actor.getChild(0).setH(180)

        mask = BitMask32()
        mask.setBit(1)

        # This is the important one for preventing ray-collisions.
        # The other is more a gameplay decision.
        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

        # Since our "Game" object is the "ShowBase" object,
        # we can access it via the global "base" variable.
        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)
        
        # This stores the previous position of the mouse,
        # as a fall-back in case we don't get a good position
        # on a given update.
        self.lastMousePos = Vec2(0, 0)

        # Construct a plane facing upwards, and centred at (0, 0, 0)
        self.groundPlane = Plane(Vec3(0, 0, 1), Vec3(0, 0, 0))
        
        #Lasers
        self.ray = CollisionRay(0, 0, 0, 0, 1, 0)

        rayNode = CollisionNode("playerRay")
        rayNode.addSolid(self.ray)

        # After we've made our ray-node:
        mask = BitMask32()

        # Note that we set a different bit here!
        # This means that the ray's mask and
        # the collider's mask don't match, and
        # so the ray won't collide with the
        # collider.
        mask.setBit(2)
        rayNode.setFromCollideMask(mask)

        mask = BitMask32()
        rayNode.setIntoCollideMask(mask)                

        self.rayNodePath = render.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()

        # We want this ray to collide with things, so
        # tell our traverser about it. However, note that,
        # unlike with "CollisionHandlerPusher", we don't
        # have to tell our "CollisionHandlerQueue" about it.
        base.cTrav.addCollider(self.rayNodePath, self.rayQueue)

        # A nice laser-beam model to show our laser
        self.beamModel = loader.loadModel("Models/Misc/bambooLaser")
        self.beamModel.reparentTo(self.actor)
        self.beamModel.setZ(1.5)
        # This prevents lights from affecting this particular node
        self.beamModel.setLightOff()
        # We don't start out firing the laser, so 
        # we have it initially hidden.
        self.beamModel.hide()

        self.beamHitModel = loader.loadModel("Models/Misc/bambooLaserHit")
        self.beamHitModel.reparentTo(render)
        self.beamHitModel.setZ(1.5)
        self.beamHitModel.setLightOff()
        self.beamHitModel.hide()

        self.beamHitPulseRate = 0.15
        self.beamHitTimer = 0

        self.damagePerSecond = -5.0

        self.score = 0

        self.scoreUI = OnscreenText(text = "0",
                                    pos = (-1.3, 0.825),
                                    mayChange = True,
                                    align = TextNode.ALeft,
                                    font = base.font)

        self.healthIcons = []
        for i in range(self.maxHealth):
            icon = OnscreenImage(image = "UI/health.png",
                                 pos = (-1.275 + i*0.075, 0, 0.95),
                                 scale = 0.04)
            icon.setTransparency(True)
            self.healthIcons.append(icon)

        self.damageTakenModel = loader.loadModel("Models/Misc/playerHit")
        self.damageTakenModel.setLightOff()
        self.damageTakenModel.setZ(1.0)
        self.damageTakenModel.reparentTo(self.actor)
        self.damageTakenModel.hide()

        self.damageTakenModelTimer = 0
        self.damageTakenModelDuration = 0.15

        self.laserSoundNoHit = loader.loadSfx("Sounds/laserNoHit.ogg")
        self.laserSoundNoHit.setLoop(True)
        self.laserSoundHit = loader.loadSfx("Sounds/laserHit.ogg")
        self.laserSoundHit.setLoop(True)

        self.beamHitLight = PointLight("beamHitLight")
        self.beamHitLight.setColor(Vec4(0.1, 1.0, 0.2, 1))
        self.beamHitLight.setAttenuation((1.0, 0.1, 0.5))
        self.beamHitLightNodePath = render.attachNewNode(self.beamHitLight)

        self.hurtSound = loader.loadSfx("Sounds/FemaleDmgNoise.ogg")

        # This vector is used to calculate the orientation for
        # the character's model. Since the character faces along
        # the y-direction, we use the y-axis.
        self.yVector = Vec2(0, 1)

        self.actor.loop("stand")

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.walking = False

        # If we're  pushing a movement key, add a relevant amount
        # to our velocity.
        if keys["up"]:
            self.walking = True
            self.velocity.addY(self.acceleration*dt)
        if keys["down"]:
            self.walking = True
            self.velocity.addY(-self.acceleration*dt)
        if keys["left"]:
            self.walking = True
            self.velocity.addX(-self.acceleration*dt)
        if keys["right"]:
            self.walking = True
            self.velocity.addX(self.acceleration*dt)
        

        # Run the appropriate animation for our current state.
        # See the text below this for an explanation
        if self.walking:
            standControl = self.actor.getAnimControl("stand")
            if standControl.isPlaying():
                standControl.stop()

            walkControl = self.actor.getAnimControl("walk")
            if not walkControl.isPlaying():
                self.actor.loop("walk")
        else:
            standControl = self.actor.getAnimControl("stand")
            if not standControl.isPlaying():
                self.actor.stop("walk")
                self.actor.loop("stand")

        # It's possible that we'll find that we
        # don't have the mouse--such as if the pointer
        # is outside of the game-window. In that case,
        # just use the previous position.
        mouseWatcher = base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            mousePos = mouseWatcher.getMouse()
        else:
            mousePos = self.lastMousePos

        mousePos3D = Point3()
        nearPoint = Point3()
        farPoint = Point3()

        # Get the 3D line corresponding with the 
        # 2D mouse-position.
        # The "extrude" method will store its result in the
        # "nearPoint" and "farPoint" objects.
        base.camLens.extrude(mousePos, nearPoint, farPoint)

        # Get the 3D point at which the 3D line
        # intersects our ground-plane.
        # Similarly to the above, the "intersectsLine" method
        # will store its result in the "mousePos3D" object.
        self.groundPlane.intersectsLine(mousePos3D,
                                        render.getRelativePoint(base.camera, nearPoint),
                                        render.getRelativePoint(base.camera, farPoint))

        firingVector = Vec3(mousePos3D - self.actor.getPos())
        firingVector2D = firingVector.getXy()
        firingVector2D.normalize()
        firingVector.normalize()

        heading = self.yVector.signedAngleDeg(firingVector2D)

        self.actor.setH(heading)

        # In short, run a timer, and use the timer in a sine-function
        # to pulse the scale of the beam-hit model. When the timer
        # runs down (and the scale is at its lowest), reset the timer
        # and randomise the beam-hit model's rotation.
        self.beamHitTimer -= dt
        if self.beamHitTimer <= 0:
            self.beamHitTimer = self.beamHitPulseRate
            self.beamHitModel.setH(random.uniform(0.0, 360.0))
        self.beamHitModel.setScale(math.sin(self.beamHitTimer*3.142/self.beamHitPulseRate)*0.4 + 0.9)
       
        # If we're pressing the "shoot" button, check
        # whether the ray has hit anything, and if so,
        # examine the collision-entry for the first hit.
        # If the thing hit has an "owner" Python-tag, then
        # it's a GameObject, and should try to take damage--
        # with the exception if "TrapEnemies",
        # which are invulnerable.
        if keys["shoot"]:
            if self.rayQueue.getNumEntries() > 0:
                scoredHit = False                
                self.rayQueue.sortEntries()
                rayHit = self.rayQueue.getEntry(0)
                hitPos = rayHit.getSurfacePoint(render)

                hitNodePath = rayHit.getIntoNodePath()
                print (hitNodePath)
                if hitNodePath.hasPythonTag("owner"):
                    hitObject = hitNodePath.getPythonTag("owner")
                    if not isinstance(hitObject, TrapEnemy):
                        hitObject.alterHealth(self.damagePerSecond*dt)
                        scoredHit = True
                
                # Find out how long the beam is, and scale the
                # beam-model accordingly.
                beamLength = (hitPos - self.actor.getPos()).length()
                self.beamModel.setSy(beamLength)

                self.beamModel.show()

                if scoredHit:
                    if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                        self.laserSoundNoHit.stop()
                    if self.laserSoundHit.status() != AudioSound.PLAYING:
                        self.laserSoundHit.play()

                    self.beamHitModel.show()

                    self.beamHitModel.setPos(hitPos)
                    self.beamHitLightNodePath.setPos(hitPos + Vec3(0, 0, 0.5))

                    # If the light hasn't already been set here, set it
                    if not render.hasLight(self.beamHitLightNodePath):
                        # Apply the light to the scene, so that it
                        # illuminates things
                        render.setLight(self.beamHitLightNodePath)
                else:
                    if self.laserSoundHit.status() == AudioSound.PLAYING:
                        self.laserSoundHit.stop()
                    if self.laserSoundNoHit.status() != AudioSound.PLAYING:
                        self.laserSoundNoHit.play()

                    # If the light has been set here, remove it
                    # See explanation in the tutorial-text below...
                    if render.hasLight(self.beamHitLightNodePath):
                        # Clear the light from the scene, so that it
                        # no longer illuminates anything
                        render.clearLight(self.beamHitLightNodePath)

                    self.beamHitModel.hide()
        else:
            if render.hasLight(self.beamHitLightNodePath):
                # Clear the light from the scene
                render.clearLight(self.beamHitLightNodePath)

            # If we're not shooting, don't show the beam-model.
            self.beamModel.hide()
            self.beamHitModel.hide()

            if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                self.laserSoundNoHit.stop()
            if self.laserSoundHit.status() == AudioSound.PLAYING:
                self.laserSoundHit.stop()

        if firingVector.length() > 0.001:
            self.ray.setOrigin(self.actor.getPos())
            self.ray.setDirection(firingVector)

        self.lastMousePos = mousePos

        if self.damageTakenModelTimer > 0:
            self.damageTakenModelTimer -= dt
            self.damageTakenModel.setScale(2.0 - self.damageTakenModelTimer/self.damageTakenModelDuration)
            if self.damageTakenModelTimer <= 0:
                self.damageTakenModel.hide()


    def updateScore(self):
        self.scoreUI.setText(str(self.score))

    def alterHealth(self, dHealth):
        GameObject.alterHealth(self, dHealth)

        self.updateHealthUI()

        self.damageTakenModel.show()
        self.damageTakenModel.setH(random.uniform(0.0, 360.0))
        self.damageTakenModelTimer = self.damageTakenModelDuration

        self.hurtSound.play()

    def updateHealthUI(self):
        for index, icon in enumerate(self.healthIcons):
            if index < self.health:
                icon.show()
            else:
                icon.hide()
    
    def cleanup(self):
        self.scoreUI.removeNode()

        for icon in self.healthIcons:
            icon.removeNode()

        self.beamHitModel.removeNode()

        base.cTrav.removeCollider(self.rayNodePath)

        self.laserSoundHit.stop()
        self.laserSoundNoHit.stop()

        render.clearLight(self.beamHitLightNodePath)
        self.beamHitLightNodePath.removeNode()

        GameObject.cleanup(self)

class Enemy(GameObject):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        GameObject.__init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName)

        # This is the number of points to award
        # if the enemy is killed.
        self.scoreValue = 1

    def update(self, player, dt):
        # In short, update as a GameObject, then
        # run whatever enemy-specific logic is to be done.
        # The use of a separate "runLogic" method
        # allows us to customise that specific logic
        # to the enemy, without re-writing the rest.

        GameObject.update(self, dt)

        self.runLogic(player, dt)

        # As with the player, play the appropriate animation.
        if self.walking:
            walkingControl = self.actor.getAnimControl("walk")
            if not walkingControl.isPlaying():
                self.actor.loop("walk")
        else:
            spawnControl = self.actor.getAnimControl("spawn")
            if spawnControl is None or not spawnControl.isPlaying():
                attackControl = self.actor.getAnimControl("attack")
                if attackControl is None or not attackControl.isPlaying():
                    standControl = self.actor.getAnimControl("stand")
                    if not standControl.isPlaying():
                        self.actor.loop("stand")


    def runLogic(self, player, dt):
        pass

class WalkingEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos,
                       "Models/Misc/simpleEnemy",
                       {
                        "stand" : "Models/Misc/simpleEnemy-stand",
                        "walk" : "Models/Misc/simpleEnemy-walk",
                        "attack" : "Models/Misc/simpleEnemy-attack",
                        "die" : "Models/Misc/simpleEnemy-die",
                        "spawn" : "Models/Misc/simpleEnemy-spawn"
                        },
                       3.0,
                       7.0,
                       "walkingEnemy")

        self.attackDistance = 0.75
        self.attackDelay = 0.3
        self.attackDelayTimer = 0
        self.attackWaitTimer = 0
        self.acceleration = 100.0

        mask = BitMask32()
        mask.setBit(2)

        self.collider.node().setIntoCollideMask(mask)

        self.attackSegment = CollisionSegment(0, 0, 0, 1, 0, 0)
        
        segmentNode = CollisionNode("enemyAttackSegment")
        segmentNode.addSolid(self.attackSegment)

        # A mask that matches the player's, so that
        # the enemy's attack will hit the player-character,
        # but not the enemy-character (or other enemies)
        mask = BitMask32()
        mask.setBit(1)

        segmentNode.setFromCollideMask(mask)

        mask = BitMask32()

        segmentNode.setIntoCollideMask(mask)

        self.attackSegmentNodePath = render.attachNewNode(segmentNode)
        self.segmentQueue = CollisionHandlerQueue()

        base.cTrav.addCollider(self.attackSegmentNodePath, self.segmentQueue)

        # How much damage the enemy's attack does
        # That is, this results in the player-character's
        # health being reduced by one.
        self.attackDamage = -1

        self.deathSound = loader.loadSfx("Sounds/enemyDie.ogg")
        self.attackSound = loader.loadSfx("Sounds/enemyAttack.ogg")

        # A reference vector, used to determine
        # which way to face the Actor.
        # Since the character faces along
        # the y-direction, we use the y-axis.
        self.yVector = Vec2(0, 1)

        self.actor.play("spawn")

    def runLogic(self, player, dt):
        spawnControl = self.actor.getAnimControl("spawn")
        if spawnControl is not None and spawnControl.isPlaying():
            return

        # In short: find the vector between
        # this enemy and the player.
        # If the enemy is far from the player,
        # use that vector to move towards the player.
        # Otherwise, just stop for now.
        # Finally, face the player.
        vectorToPlayer = player.actor.getPos() - self.actor.getPos()

        vectorToPlayer2D = vectorToPlayer.getXy()
        distanceToPlayer = vectorToPlayer2D.length()

        vectorToPlayer2D.normalize()

        heading = self.yVector.signedAngleDeg(vectorToPlayer2D)

        self.attackSegment.setPointA(self.actor.getPos())
        self.attackSegment.setPointB(self.actor.getPos() + self.actor.getQuat().getForward()*self.attackDistance)

        if distanceToPlayer > self.attackDistance*0.9:
            attackControl = self.actor.getAnimControl("attack")
            if not attackControl.isPlaying():
                self.walking = True
                vectorToPlayer.setZ(0)
                vectorToPlayer.normalize()
                self.velocity += vectorToPlayer*self.acceleration*dt
                self.attackWaitTimer = 0.2
                self.attackDelayTimer = 0
        else:
            self.walking = False
            self.velocity.set(0, 0, 0)

            # If we're waiting for an attack to land...
            if self.attackDelayTimer > 0:
                self.attackDelayTimer -= dt
                # If the time has come for the attack to land...
                if self.attackDelayTimer <= 0:
                    # Check for a hit..
                    if self.segmentQueue.getNumEntries() > 0:
                        self.segmentQueue.sortEntries()
                        segmentHit = self.segmentQueue.getEntry(0)

                        hitNodePath = segmentHit.getIntoNodePath()
                        if hitNodePath.hasPythonTag("owner"):
                            # Apply damage!
                            hitObject = hitNodePath.getPythonTag("owner")
                            hitObject.alterHealth(self.attackDamage)
                            self.attackWaitTimer = 1.0
            # If we're instead waiting to be allowed to attack...
            elif self.attackWaitTimer > 0:
                self.attackWaitTimer -= dt
                # If the wait has ended...
                if self.attackWaitTimer <= 0:
                    # Start an attack!
                    # (And set the wait-timer to a random amount,
                    #  to vary things a little bit.)
                    self.attackWaitTimer = random.uniform(0.5, 0.7)
                    self.attackDelayTimer = self.attackDelay
                    self.actor.play("attack")
                    self.attackSound.play()

        self.actor.setH(heading)
    
    def alterHealth(self, dHealth):
        Enemy.alterHealth(self, dHealth)
        self.updateHealthVisual()

    def updateHealthVisual(self):
        perc = self.health/self.maxHealth
        if perc < 0:
            perc = 0
        # The parameters here are red, green, blue, and alpha
        self.actor.setColorScale(perc, perc, perc, 1)
    
    def cleanup(self):
        base.cTrav.removeCollider(self.attackSegmentNodePath)
        self.attackSegmentNodePath.removeNode()

        GameObject.cleanup(self)


class TrapEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos,
                       "Models/Misc/trap",
                       {
                        "stand" : "Models/Misc/trap-stand",
                        "walk" : "Models/Misc/trap-walk",
                        },
                       100.0,
                       10.0,
                       "trapEnemy")

        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)

        self.moveInX = False

        self.moveDirection = 0

        # This will allow us to prevent multiple
        # collisions with the player during movement
        self.ignorePlayer = False

        self.impactSound = loader.loadSfx("Sounds/trapHitsSomething.ogg")
        self.stopSound = loader.loadSfx("Sounds/trapStop.ogg")
        self.movementSound = loader.loadSfx("Sounds/trapSlide.ogg")
        self.movementSound.setLoop(True)

    def runLogic(self, player, dt):
        if self.moveDirection != 0:
            self.walking = True
            if self.moveInX:
                self.velocity.addX(self.moveDirection*self.acceleration*dt)
            else:
                self.velocity.addY(self.moveDirection*self.acceleration*dt)
        else:
            self.walking = False
            diff = player.actor.getPos() - self.actor.getPos()
            if self.moveInX:
                detector = diff.y
                movement = diff.x
            else:
                detector = diff.x
                movement = diff.y

            if abs(detector) < 0.5:
                self.moveDirection = math.copysign(1, movement)
                self.movementSound.play()

    def alterHealth(self, dHealth):
        pass

    def cleanup(self):
        self.movementSound.stop()

        Enemy.cleanup(self)