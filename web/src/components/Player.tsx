import { useEffect, useRef } from "react";

// Minimal typing for the YouTube IFrame API we use.
declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiPromise: Promise<void> | null = null;
function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve) => {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    window.onYouTubeIframeAPIReady = () => resolve();
    document.head.appendChild(tag);
  });
  return apiPromise;
}

type Props = {
  videoId: string;
  onTime: (t: number) => void;
  onReady: (seek: (t: number) => void) => void;
};

export default function Player({ videoId, onTime, onReady }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => {
    let interval: number | undefined;
    let cancelled = false;

    loadYouTubeApi().then(() => {
      if (cancelled || !hostRef.current) return;
      playerRef.current = new window.YT.Player(hostRef.current, {
        videoId,
        playerVars: { rel: 0, modestbranding: 1 },
        events: {
          onReady: () => {
            onReady((t: number) => playerRef.current?.seekTo(t, true));
            interval = window.setInterval(() => {
              const t = playerRef.current?.getCurrentTime?.();
              if (typeof t === "number") onTime(t);
            }, 250);
          },
        },
      });
    });

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
      playerRef.current?.destroy?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  return (
    <div className="player">
      <div ref={hostRef} />
    </div>
  );
}
