#include <stdio.h>
#include <iostream>
#include <SDL2/SDL.h>
#include <vector>
#include <chrono>
#include <random>

#include "main.h"

using namespace std::chrono;
using namespace std;

typedef struct {
    SDL_Renderer *renderer;
    SDL_Window *window;
    int targetFrameTime;
} App;

void initSDL(App *app) {
    int rendererFlags, windowFlags;

    rendererFlags = SDL_RENDERER_ACCELERATED;
    windowFlags = SDL_WINDOW_FULLSCREEN;

    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("Couldn't initialise SDL: %s\n", SDL_GetError());
        exit(1);
    }

    app->window = SDL_CreateWindow("Snake", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, SCREEN_WIDTH, SCREEN_HEIGHT, windowFlags);

    if (!app->window) {
        printf("Failed to open %d x %d window: %s\n", SCREEN_WIDTH, SCREEN_HEIGHT, SDL_GetError());
        exit(1);
    }

    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "linear");

    app->renderer = SDL_CreateRenderer(app->window, -1, rendererFlags);

    if (!app->renderer) {
        printf("Failed to create renderer: %s\n", SDL_GetError());
        exit(1);
    }
}

void drawRect(SDL_Renderer *renderer, SDL_Rect rect, SDL_Color color) {
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_RenderFillRect(renderer, &rect);
}

typedef struct Part {
    int x;
    int y;
} Part;

bool drawSnake(App* app, vector<Part> snake) {
    /* Returns true if there was a collision between parts in the snake */

    bool collided = false;

    Part part;
    SDL_Rect rect;
    SDL_Color color;

    Part head = snake[0];

    for (int i = 0; i < snake.size(); i++) {
        part = snake[i];

        if (i != 0 && part.x == head.x && part.y == head.y) {
            collided = true;
        }

        rect.x = part.x * PART_SIZE;
        rect.y = part.y * PART_SIZE;
        rect.w = PART_SIZE;
        rect.h = PART_SIZE;

        color.r = 0;
        color.g = 255;
        color.b = 0;
        color.a = 255;

        drawRect(app->renderer, rect, color);
    }

    return collided;
}

void moveSnake(vector<Part>* snake, int snakeDir, bool grow) {
    Part newHead;
    Part head = snake->front();

    switch (snakeDir) {
        case 0:
            newHead.x = head.x;
            newHead.y = head.y - 1;
            break;
        case 1:
            newHead.x = head.x + 1;
            newHead.y = head.y;
            break;
        case 2:
            newHead.x = head.x;
            newHead.y = head.y + 1;
            break;
        case 3:
            newHead.x = head.x - 1;
            newHead.y = head.y;
            break;
    }

    snake->insert(snake->begin(), newHead);

    if (!grow) {
        snake->pop_back();
    }
}

void drawApple(App* app, Part* apple) {
    drawRect(app->renderer, {apple->x * PART_SIZE, apple->y * PART_SIZE, PART_SIZE, PART_SIZE}, {255, 0, 0, 255});
}

int time_ms() {
    int ms = duration_cast<milliseconds>(
        system_clock::now().time_since_epoch()
    ).count();

    return ms;
}

int randint(int min, int max) {
    int range = max - min + 1;
    return rand() % range + min;
}

void moveApple(Part* apple, vector<Part> snake) {
    int x;
    int y;

    Part part;
    bool foundPos;
    while (!foundPos) {
        x = randint(0, GAME_WIDTH-1);
        y = randint(0, GAME_HEIGHT-1);

        foundPos = true;
        for (int i = 0; i < snake.size(); i++) {
            part = snake[i];

            if (x == part.x && y == part.y) {
                foundPos = false;
            }
        }
    }

    apple->x = x; 
    apple->y = y;
}

int main() {
    App app;
    app.targetFrameTime = (1.0 / FPS) * 1000;

    initSDL(&app);

    Part head = {GAME_WIDTH / 2, GAME_HEIGHT / 2};
    Part tail = {GAME_WIDTH / 2 + 1, GAME_HEIGHT / 2};

    vector<Part> snake;

    snake.push_back(head);
    snake.push_back(tail);

    int snakeDir = 3; // 0 up, 1 right, 2 down, 3 left
    int desiredDir = 3;
    bool ateApple = false;

    Part apple;

    moveApple(&apple, snake);

    int score = 0;
    bool collided = false;

    bool paused = false;
    int lastUpdate = time_ms();

    while (true) {
        SDL_SetRenderDrawColor(app.renderer, 0, 0, 0, 255);
        SDL_RenderClear(app.renderer);

        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
                case SDL_QUIT:
                    exit(0);
                    break;

                case SDL_KEYDOWN:
                    switch (event.key.keysym.scancode) {
                        case SDL_SCANCODE_UP:
                            if (snakeDir != 2) {
                                desiredDir = 0;
                                paused = false;
                            }
                            break;

                        case SDL_SCANCODE_RIGHT:
                            if (snakeDir != 3) {
                                desiredDir = 1;
                                paused = false;
                            }
                            break;

                        case SDL_SCANCODE_DOWN:
                            if (snakeDir != 0) {
                                desiredDir = 2;
                                paused = false;
                            }
                            break;

                        case SDL_SCANCODE_LEFT:
                            if (snakeDir != 1) {
                                desiredDir = 3;
                                paused = false;
                            }
                            break;

                        case SDL_SCANCODE_SPACE:
                            paused = !paused;
                            lastUpdate = time_ms();
                            break;

                        case SDL_SCANCODE_ESCAPE:
                            exit(0);
                            break;
                    }

                default:
                    break;
            }
        }

        int time = time_ms(); 

        if (!paused && time - lastUpdate > 150) {
            if (snake[0].x == apple.x && snake[0].y == apple.y) {
                moveApple(&apple, snake);
                ateApple = true;
                score++;
            }

            snakeDir = desiredDir;
            moveSnake(&snake, snakeDir, ateApple);

            if (snake[0].x < 0 or snake[0].x >= GAME_WIDTH or snake[0].y < 0 or snake[0].y >= GAME_HEIGHT) {
                collided = true;
            }

            ateApple = false;
            lastUpdate = time;
        }

        drawApple(&app, &apple);
        collided = drawSnake(&app, snake) or collided;

        if (collided) {
            head = {GAME_WIDTH / 2, GAME_HEIGHT / 2};
            tail = {GAME_WIDTH / 2 + 1, GAME_HEIGHT / 2};

            snake = {};

            snake.push_back(head);
            snake.push_back(tail);

            moveApple(&apple, snake);

            snakeDir = 3; // 0 up, 1 right, 2 down, 3 left
            ateApple = false;

            collided = false;
            paused = true;
            score = 0;
        }

        SDL_RenderPresent(app.renderer);
        SDL_Delay(16);
    };

    return 0;
}