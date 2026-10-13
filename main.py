{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "17a7f7ba-c0a2-46ef-83df-44b4d1ceb6ff",
   "metadata": {},
   "outputs": [],
   "source": [
    "import pygame\n",
    "\n",
    "# Initialize Pygame\n",
    "pygame.init()\n",
    "\n",
    "# Create a game window\n",
    "screen = pygame.display.set_mode((800, 600))\n",
    "pygame.display.set_caption(\"My Card Game\")\n",
    "\n",
    "# Set colors\n",
    "GREEN = (34, 139, 85)\n",
    "WHITE = (255, 255, 255)\n",
    "\n",
    "# Create a font\n",
    "font = pygame.font.SysFont(\"Arial\", 36)\n",
    "\n",
    "running = True\n",
    "\n",
    "while running:\n",
    "    for event in pygame.event.get():\n",
    "        if event.type == pygame.QUIT:\n",
    "            running = False\n",
    "\n",
    "    screen.fill(GREEN)\n",
    "\n",
    "    text = font.render(\"WELCOME TO MY CARD GAME!\", True, WHITE)\n",
    "    screen.blit(text, (150, 250))\n",
    "\n",
    "    pygame.display.flip()\n",
    "\n",
    "pygame.quit()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "f6f83c17-8062-4e77-b440-707d1a83248b",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python [conda env:base] *",
   "language": "python",
   "name": "conda-base-py"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.7"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
