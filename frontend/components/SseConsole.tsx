import React from "react";

interface SseEvent {
  ts: string;
  stage: string;
  message?: string | object;
}

interface SseConsoleProps {
  events: SseEvent[];
  className?: string;
  maxHeight?: string;
  "data-testid"?: string;
  newestFirst?: boolean;
}

export default function SseConsole({
  events,
  className = "",
  maxHeight = "max-h-64",
  "data-testid": dataTestId = "sse-console",
  newestFirst = true,
}: SseConsoleProps) {
  if (!events.length) {
    return (
      <div
        className={`border rounded-lg p-4 bg-gray-50 ${className}`}
        data-testid={dataTestId}
      >
        <p className="text-sm text-gray-500 text-center">No events yet...</p>
      </div>
    );
  }

  return (
    <div
      className={`border rounded-lg bg-gray-900 text-green-400 font-mono text-xs ${className}`}
      data-testid={dataTestId}
    >
      <div className="p-2 border-b border-gray-700 bg-gray-800">
        <span className="text-gray-300">
          Event Stream ({events.length} events)
        </span>
      </div>
      <div className={`p-2 overflow-y-auto ${maxHeight}`}>
        <div className="space-y-1">
          {/* Show events in requested order */}
          {(newestFirst ? [...events].reverse() : events).map(
            (event, index) => {
              const timestamp = new Date(event.ts).toLocaleTimeString();
              const isError =
                event.stage.toLowerCase().includes("error") ||
                (typeof event.message === "string" &&
                  event.message.toLowerCase().includes("error"));

              return (
                <div
                  key={`${event.ts}-${index}`}
                  className={`flex gap-2 ${isError ? "text-red-400" : "text-green-400"}`}
                >
                  <span className="text-gray-500 flex-shrink-0">
                    [{timestamp}]
                  </span>
                  <span className="text-yellow-400 flex-shrink-0">
                    {event.stage}:
                  </span>
                  <span className="flex-1 break-words">
                    {typeof event.message === "string"
                      ? event.message
                      : typeof event.message === "object"
                        ? JSON.stringify(event.message, null, 2)
                        : "Started"}
                  </span>
                </div>
              );
            },
          )}
        </div>
      </div>
      <div className="p-2 border-t border-gray-700 bg-gray-800">
        <span className="text-gray-500 text-xs">
          {newestFirst
            ? "Latest events shown first"
            : "Oldest events shown first"}{" "}
          - Auto-scrolling disabled
        </span>
      </div>
    </div>
  );
}
