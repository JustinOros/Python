#!/usr/bin/python3
# Description: tankwars - A Pygame written in Python.
# Usage: python3 game-tankwars.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random, math, sys, os
from OpenGL.GLUT import glutInit, glutSolidSphere, glutSolidCube, glutBitmapCharacter, GLUT_BITMAP_HELVETICA_18
import time
import numpy as np

pygame.init()
pygame.mixer.init()
glutInit()

sound_cannon = pygame.mixer.Sound("sound-tank-cannon.mp3")
sound_reload = pygame.mixer.Sound("sound-tank-reload.mp3")
sound_move = pygame.mixer.Sound("sound-tank-movement.mp3")
sound_turret = pygame.mixer.Sound("sound-tank-turret.mp3")
sound_explosion = pygame.mixer.Sound("sound-tank-explosion.mp3")
sound_alarm = pygame.mixer.Sound("sound-tank-alarm.mp3")
sound_warning = pygame.mixer.Sound("sound-tank-warning.mp3")

pygame.mixer.music.load("music-track01.mp3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)

pygame.joystick.init()
joysticks = []
for i in range(pygame.joystick.get_count()):
    j = pygame.joystick.Joystick(i)
    j.init()
    joysticks.append(j)

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | FULLSCREEN)
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

glEnable(GL_DEPTH_TEST)
glEnable(GL_COLOR_MATERIAL)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glLightfv(GL_LIGHT0, GL_DIFFUSE, (1,1,1,1))
glEnable(GL_TEXTURE_2D)
glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(60, WIDTH/HEIGHT, 0.1, 500)
glMatrixMode(GL_MODELVIEW)

player_pos = [0,0,0]
player_angle = 0
camera_angle = 0
pitch = 0
crosshair_offset = 0
level = 1
bullets = []
enemy_bullets = []
enemies = []
enemy_speed = 2
last_fire_time = 0
FIRE_COOLDOWN = 1.5
ENEMY_FIRE_COOLDOWN = 2.0
total_enemies = 0
TANK_COLLISION_RADIUS = 4
moving_sound_playing = False
player_life = 100
player_tank_visible = True
game_over = False
game_over_time = 0
alarm_playing = False

tank_display_list = None
TANK_SCALE = 0.003

if os.path.isfile("object-tank.npy"):
    try:
        tank_data = np.load("object-tank.npy", allow_pickle=True).item()
        tank_display_list = glGenLists(1)
        glNewList(tank_display_list, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for face in tank_data['faces']:
            for vertex_idx in face:
                v = tank_data['vertices'][vertex_idx]
                glVertex3f(v[0]*TANK_SCALE, v[1]*TANK_SCALE, v[2]*TANK_SCALE)
        glEnd()
        glEndList()
    except:
        sys.exit(1)
else:
    sys.exit(1)

def spawn_enemies(level):
    global total_enemies
    enemies.clear()
    count = level*5
    total_enemies = count
    min_dist = 80
    for _ in range(count):
        while True:
            x = random.randint(-200,200)
            z = random.randint(-200,200)
            collision = math.hypot(x-player_pos[0], z-player_pos[2])<min_dist
            for e in enemies:
                if math.hypot(x-e['pos'][0], z-e['pos'][2])<min_dist:
                    collision=True
                    break
            if not collision:
                angle = random.uniform(0,360)
                target_angle = random.uniform(0,360)
                enemies.append({
                    'pos':[x,0,z],
                    'angle':angle,
                    'target_angle':target_angle,
                    'state':'rotating',
                    'move_timer':0,
                    'last_fire':0,
                    'player_detected':False,
                    'warning_played':False
                })
                break

def draw_sky():
    glDisable(GL_LIGHTING)
    glPushMatrix()
    glLoadIdentity()
    glBegin(GL_QUADS)
    glColor3f(0.53, 0.81, 0.92)
    glVertex3f(-500, -500, -500)
    glVertex3f(500, -500, -500)
    glVertex3f(500, -500, 500)
    glVertex3f(-500, -500, 500)
    glColor3f(0.2, 0.5, 0.9)
    glVertex3f(-500, 0, -500)
    glVertex3f(500, 0, -500)
    glVertex3f(500, 0, 500)
    glVertex3f(-500, 0, 500)
    glEnd()
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_grid():
    glDisable(GL_LIGHTING)
    glBegin(GL_LINES)
    grid_range = 200
    step = 1
    px, pz = player_pos[0], player_pos[2]
    for i in range(int(px - grid_range), int(px + grid_range) + 1, step):
        fade = max(0.2, 1 - abs(i - px) / grid_range)
        glColor3f(0, 1*fade, 1*fade)
        glVertex3f(i,0,pz-grid_range)
        glVertex3f(i,0,pz+grid_range)
    for i in range(int(pz - grid_range), int(pz + grid_range) + 1, step):
        fade = max(0.2, 1 - abs(i - pz) / grid_range)
        glColor3f(0, 1*fade, 1*fade)
        glVertex3f(px-grid_range,0,i)
        glVertex3f(px+grid_range,0,i)
    glEnd()
    glEnable(GL_LIGHTING)

def draw_text(x,y,text,color=(1,1,1),size=18):
    glDisable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0,WIDTH,0,HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(*color)
    glRasterPos2f(x,HEIGHT-y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_LIGHTING)

def draw_crosshair():
    glDisable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, 0, HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(1,1,1)
    glBegin(GL_LINES)
    cx = WIDTH/2 + crosshair_offset
    cy = HEIGHT/2 - 50
    glVertex2f(cx-10, cy)
    glVertex2f(cx+10, cy)
    glVertex2f(cx, cy-10)
    glVertex2f(cx, cy+10)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_LIGHTING)

def draw_bullet(x,y,z,color):
    glColor3f(*color)
    glPushMatrix()
    glTranslatef(x,y,z)
    radius = 0.2
    stacks = 8
    slices = 8
    for i in range(stacks):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0 = radius * math.sin(lat0)
        zr0 = radius * math.cos(lat0)
        lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
        z1 = radius * math.sin(lat1)
        zr1 = radius * math.cos(lat1)
        glBegin(GL_QUAD_STRIP)
        for j in range(slices + 1):
            lng = 2 * math.pi * float(j) / slices
            x_coord = math.cos(lng)
            y_coord = math.sin(lng)
            glNormal3f(x_coord * zr0, y_coord * zr0, z0)
            glVertex3f(x_coord * zr0, y_coord * zr0, z0)
            glNormal3f(x_coord * zr1, y_coord * zr1, z1)
            glVertex3f(x_coord * zr1, y_coord * zr1, z1)
        glEnd()
    glPopMatrix()

def draw_player_tank(x, z, direction=0, turret_angle=0, turret_pitch=0):
    glPushMatrix()
    glTranslatef(x, 0, z)
    glRotatef(turret_angle, 0, 1, 0)
    glColor3f(0,1,1)
    glCallList(tank_display_list)
    glPopMatrix()

def draw_enemy_tank(x, z, body_direction=0, turret_angle=0):
    distance = math.hypot(x - player_pos[0], z - player_pos[2])
    if distance >= 100:
        return
    alpha = 1.0
    if distance > 90:
        alpha = max(0, 1 - (distance-90)/10)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1,0,0,alpha)
    glPushMatrix()
    glTranslatef(x, 0, z)
    glRotatef(body_direction, 0, 1, 0)
    glPushMatrix()
    glRotatef(-90, 0, 1, 0)
    glRotatef(turret_angle - body_direction, 0, 1, 0)
    glCallList(tank_display_list)
    glPopMatrix()
    glPopMatrix()
    glDisable(GL_BLEND)

def check_tank_collision(new_pos, ignore_enemy=None, is_player=False):
    for t in enemies:
        if t is ignore_enemy:
            continue
        if math.hypot(new_pos[0]-t['pos'][0], new_pos[2]-t['pos'][2]) < TANK_COLLISION_RADIUS:
            return True
    if not is_player:
        if math.hypot(new_pos[0]-player_pos[0], new_pos[2]-player_pos[2]) < TANK_COLLISION_RADIUS:
            return True
    return False

def move_enemies(dt):
    if player_life<=0: return
    current_time = time.time()
    for e in enemies:
        distance_to_player = math.hypot(e['pos'][0]-player_pos[0], e['pos'][2]-player_pos[2])
        previously_detected = e['player_detected']
        e['player_detected'] = distance_to_player <= 100
        if e['player_detected'] and not previously_detected and not e['warning_played']:
            sound_warning.play()
            e['warning_played'] = True
        if e['player_detected']:
            e['state'] = 'hunting'
            target_dx = player_pos[0] - e['pos'][0]
            target_dz = player_pos[2] - e['pos'][2]
            e['target_angle'] = math.degrees(math.atan2(target_dx, target_dz))
        if e['state']=='rotating':
            angle_diff = (e['target_angle'] - e['angle'] + 540)%360 - 180
            max_rot = 120*dt
            if abs(angle_diff)<5:
                e['angle']=e['target_angle']
                if not e['player_detected']:
                    e['state']='moving'
                    e['move_timer']=30
                else:
                    e['state']='hunting'
            else:
                e['angle'] += max_rot if angle_diff>0 else -max_rot
                e['angle']%=360
        elif e['state']=='moving':
            dx = math.sin(math.radians(e['angle']))
            dz = math.cos(math.radians(e['angle']))
            new_pos = [e['pos'][0]+dx*enemy_speed*dt,0,e['pos'][2]+dz*enemy_speed*dt]
            if not check_tank_collision(new_pos,ignore_enemy=e):
                e['pos'][0]=new_pos[0]
                e['pos'][2]=new_pos[2]
            else:
                e['target_angle']=random.uniform(0,360)
                e['state']='rotating'
            e['move_timer']-=dt
            if e['move_timer']<=0:
                if random.random()<0.3:
                    e['target_angle']=random.uniform(0,360)
                    e['state']='rotating'
                else:
                    e['move_timer']=30
        elif e['state']=='hunting':
            target_dx = player_pos[0]-e['pos'][0]
            target_dz = player_pos[2]-e['pos'][2]
            target_angle = math.degrees(math.atan2(target_dx, target_dz))
            angle_diff = (target_angle - e['angle'] + 540)%360 - 180
            max_rot = 90*dt
            if abs(angle_diff)<max_rot:
                e['angle']=target_angle
            else:
                e['angle']+= max_rot if angle_diff>0 else -max_rot
                e['angle']%=360
            if abs(angle_diff)<45:
                dx = math.sin(math.radians(e['angle']))
                dz = math.cos(math.radians(e['angle']))
                new_pos = [e['pos'][0]+dx*enemy_speed*dt,0,e['pos'][2]+dz*enemy_speed*dt]
                if not check_tank_collision(new_pos,ignore_enemy=e):
                    e['pos'][0]=new_pos[0]
                    e['pos'][2]=new_pos[2]
            if abs(angle_diff)<15 and distance_to_player<=50:
                if current_time - e.get('last_fire',0) > ENEMY_FIRE_COOLDOWN:
                    e['last_fire']=current_time
                    bx,by,bz = e['pos'][0],1,e['pos'][2]
                    dx = math.sin(math.radians(e['angle']))
                    dz = math.cos(math.radians(e['angle']))
                    dy=0
                    enemy_bullets.append([bx,by,bz,dx,dy,dz,current_time])
                    sound_cannon.play()
            if not e['player_detected']:
                e['target_angle']=random.uniform(0,360)
                e['state']='rotating'

spawn_enemies(level)
clock = pygame.time.Clock()
running=True
radar_sweep_angle=0.0

while running:
    dt=clock.tick(60)/1000
    keys=pygame.key.get_pressed()
    move_vector=[0,0,0]
    fire_pressed=False
    speed_multiplier = 2 if keys[K_LSHIFT] or keys[K_RSHIFT] else 1

    for joystick in joysticks:
        lx=joystick.get_axis(0)
        ly=joystick.get_axis(1)
        if abs(lx)>0.2: move_vector[0]+=math.cos(math.radians(player_angle))*lx*dt*5*speed_multiplier; move_vector[2]+=math.sin(math.radians(player_angle))*lx*dt*5*speed_multiplier
        if abs(ly)>0.2: move_vector[0]+=math.sin(math.radians(player_angle))*(-ly)*dt*5*speed_multiplier; move_vector[2]-=math.cos(math.radians(player_angle))*(-ly)*dt*5*speed_multiplier
        if joystick.get_button(0) or joystick.get_button(4) or joystick.get_button(5): fire_pressed=True
        if joystick.get_button(6): crosshair_offset-=5
        if joystick.get_button(7): crosshair_offset+=5

    if keys[K_w]: move_vector[0]+=math.sin(math.radians(player_angle))*5*dt*speed_multiplier; move_vector[2]-=math.cos(math.radians(player_angle))*5*dt*speed_multiplier
    if keys[K_s]: move_vector[0]-=math.sin(math.radians(player_angle))*5*dt*speed_multiplier; move_vector[2]+=math.cos(math.radians(player_angle))*5*dt*speed_multiplier
    if keys[K_a]: move_vector[0]-=math.cos(math.radians(player_angle))*5*dt*speed_multiplier; move_vector[2]-=math.sin(math.radians(player_angle))*5*dt*speed_multiplier
    if keys[K_d]: move_vector[0]+=math.cos(math.radians(player_angle))*5*dt*speed_multiplier; move_vector[2]+=math.sin(math.radians(player_angle))*5*dt*speed_multiplier

    moving=any(move_vector)
    if moving and not moving_sound_playing: sound_move.play(-1); moving_sound_playing=True
    elif not moving and moving_sound_playing: sound_move.stop(); moving_sound_playing=False

    proposed_pos=[player_pos[0]+move_vector[0],0,player_pos[2]+move_vector[2]]
    if not check_tank_collision(proposed_pos,is_player=True):
        player_pos[0]=proposed_pos[0]; player_pos[2]=proposed_pos[2]

    for event in pygame.event.get():
        if event.type==QUIT: running=False
        if event.type==KEYDOWN:
            if event.key==K_ESCAPE: running=False
            if event.key==K_SPACE: fire_pressed=True
            if event.key==K_v: player_tank_visible = not player_tank_visible
        if event.type==MOUSEBUTTONDOWN and event.button==1: fire_pressed=True
        if event.type==pygame.USEREVENT+1:
            sound_reload.play()
            pygame.time.set_timer(pygame.USEREVENT+1,0)

    current_time=time.time()
    if fire_pressed and (current_time - last_fire_time>=FIRE_COOLDOWN):
        last_fire_time=current_time
        rad_cam = math.radians(player_angle)
        rad_pitch = math.radians(pitch)
        forward_x = math.sin(rad_cam) * math.cos(rad_pitch)
        forward_y = math.sin(rad_pitch)
        forward_z = -math.cos(rad_cam) * math.cos(rad_pitch)
        barrel_length = 3.0
        barrel_base_height = 1.2
        bx = player_pos[0] + forward_x * barrel_length
        by = player_pos[1] + barrel_base_height + forward_y * barrel_length
        bz = player_pos[2] + forward_z * barrel_length
        dx = forward_x
        dy = forward_y
        dz = forward_z
        bullets.append([bx,by,bz,dx,dy,dz,current_time])
        sound_cannon.play()
        pygame.time.set_timer(pygame.USEREVENT+1,500)

    mx,my=pygame.mouse.get_rel()
    camera_angle+=mx*0.1
    player_angle=camera_angle
    pitch-=my*0.1
    pitch=max(-10,min(10,pitch))

    for b in bullets:
        b[0]+=b[3]*60*dt
        b[1] += b[4] * 60 * dt
        b[2]+=b[5]*60*dt

    for b in enemy_bullets:
        b[0]+=b[3]*60*dt
        b[1]+=b[4]*30*dt
        b[2]+=b[5]*60*dt

    current_time=time.time()
    new_bullets=[]
    for b in bullets[:]:
        keep=True
        if b[1]<0 or (current_time-b[6])>10.0:
            keep=False
        else:
            for e in enemies[:]:
                if abs(b[0]-e['pos'][0])<2 and abs(b[2]-e['pos'][2])<2 and abs(b[1]-1)<2:
                    enemies.remove(e)
                    total_enemies-=1
                    sound_explosion.set_volume(0.5)
                    sound_explosion.play()
                    keep=False
                    break
        if keep: new_bullets.append(b)
    bullets=new_bullets

    new_enemy_bullets=[]
    for b in enemy_bullets[:]:
        keep=True
        if b[1]<0 or (current_time-b[6])>10.0:
            keep=False
        else:
            if player_life>0 and abs(b[0]-player_pos[0])<2 and abs(b[2]-player_pos[2])<2:
                player_life-=25
                sound_explosion.play()
                keep=False
                if player_life<=0:
                    game_over=True
                    game_over_time=time.time()
                    pygame.mixer.music.stop()
        if keep: new_enemy_bullets.append(b)
    enemy_bullets=new_enemy_bullets

    if player_life <= 25 and not alarm_playing:
        sound_alarm.play(-1)
        alarm_playing = True
    elif player_life > 25 and alarm_playing:
        sound_alarm.stop()
        alarm_playing = False

    move_enemies(dt)
    if len(enemies)==0 and not game_over:
        level+=1
        player_life=100
        spawn_enemies(level)

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    cam_height=8
    cam_distance=25

    rad_cam=math.radians(camera_angle)
    rad_pitch=math.radians(pitch)

    eye_x=player_pos[0] - math.sin(rad_cam)*cam_distance
    eye_y=cam_height
    eye_z=player_pos[2] + math.cos(rad_cam)*cam_distance

    dx=math.sin(rad_cam)*math.cos(rad_pitch)
    dy=math.sin(rad_pitch)
    dz=-math.cos(rad_cam)*math.cos(rad_pitch)

    center_x=player_pos[0] + dx*50
    center_y=cam_height + dy*50
    center_z=player_pos[2] + dz*50

    gluLookAt(eye_x,eye_y,eye_z,center_x,center_y,center_z,0,1,0)
    glLightfv(GL_LIGHT0, GL_POSITION, (eye_x,eye_y,eye_z,1))

    turret_angle = player_angle
    turret_pitch = pitch

    draw_sky()
    draw_grid()
    if player_tank_visible:
        draw_player_tank(player_pos[0], player_pos[2], 0, -player_angle + 93, 0)

    for e in enemies:
        dx = player_pos[0] - e['pos'][0]
        dz = player_pos[2] - e['pos'][2]
        enemy_turret_angle = math.degrees(math.atan2(dx, dz))
        draw_enemy_tank(e['pos'][0], e['pos'][2], body_direction=e['angle'], turret_angle=enemy_turret_angle)

    for b in bullets:
        draw_bullet(b[0],b[1],b[2],(0,1,1))
    for b in enemy_bullets:
        draw_bullet(b[0],b[1],b[2],(1,0,0))
    draw_crosshair()
    draw_text(WIDTH-100, HEIGHT-10,f"Enemies: {total_enemies}",color=(0,1,0))
    draw_text(10,HEIGHT-10,f"Life: {player_life}%",color=(0,1,0))
    if game_over:
        draw_text(WIDTH//2-70, HEIGHT//2-20, "GAME OVER", color=(1,0,0))
        if time.time()-game_over_time>1:
            running=False

    glDisable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, 0, HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    radar_radius=80
    radar_x=WIDTH-radar_radius-20
    radar_y=HEIGHT-radar_radius-20
    glColor3f(0,0.5,0)
    glBegin(GL_LINE_LOOP)
    for i in range(360):
        theta=math.radians(i)
        x=radar_x+radar_radius*math.cos(theta)
        y=radar_y+radar_radius*math.sin(theta)
        glVertex2f(x,y)
    glEnd()
    sweep_length=radar_radius
    sweep_rad=math.radians(radar_sweep_angle)
    ex=radar_x+math.sin(sweep_rad)*sweep_length
    ey=radar_y+math.cos(sweep_rad)*sweep_length
    glColor3f(0,1,0)
    glLineWidth(2)
    glBegin(GL_LINES)
    glVertex2f(radar_x,radar_y)
    glVertex2f(ex,ey)
    glEnd()
    radar_sweep_angle=(radar_sweep_angle+120*dt)%360
    glColor3f(0,1,1)
    glPointSize(6)
    glBegin(GL_POINTS)
    glVertex2f(radar_x,radar_y)
    glEnd()
    for idx,e in enumerate(enemies):
        dx=e['pos'][0]-player_pos[0]
        dz=e['pos'][2]-player_pos[2]
        distance=math.hypot(dx,dz)
        max_display_distance=100
        display_distance=min(distance,max_display_distance)/max_display_distance*radar_radius
        angle=math.atan2(dx,-dz)-math.radians(player_angle)
        ex=radar_x+math.sin(angle)*display_distance
        ey=radar_y+math.cos(angle)*display_distance
        glColor3f(1,0,0)
        glPointSize(4)
        glBegin(GL_POINTS)
        glVertex2f(ex,ey)
        glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_LIGHTING)

    pygame.display.flip()

pygame.quit()
