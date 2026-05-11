import { useEffect, useState } from "react";

export function useSSE(url: string | null): string | null {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event: MessageEvent<string>) => {
      if (event.data === "__DONE__") {
        eventSource.close();
        return;
      }
      setMessage(event.data);
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [url]);

  return message;
}
