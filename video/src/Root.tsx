import React from "react";
import { Composition } from "remotion";
import { BrandFilm, BRAND_FILM_FRAMES } from "./BrandFilm";
import { FPS, HEIGHT, WIDTH } from "./brand";
import { Scene1, SCENE1_DURATION_FRAMES } from "./Scene1";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BrandFilm"
        component={BrandFilm}
        durationInFrames={BRAND_FILM_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Scene1"
        component={Scene1}
        durationInFrames={SCENE1_DURATION_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
