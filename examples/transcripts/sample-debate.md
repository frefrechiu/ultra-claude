# Transcript: Should we add an undo button to the editor?

<!-- turn:1 agent:Architect -->

## Architect (high-level design)

I'd start with a single linear undo stack -- not branching, not multi-level. The data shape: `Stack<EditorAction>` where `EditorAction` is `{type, payload, inverse_payload}`. Push on every edit; pop on undo and apply `inverse_payload`. Simplicity wins until proven otherwise.

Open questions:
1. What's the cap on stack depth? Memory grows linearly with edit count.
2. Do we persist across sessions? If yes, that's a separate problem (storage strategy, schema migrations).
3. Are we redoing? If yes, the stack becomes a deque and we track a cursor.

I'd say: cap at 100 actions, no persistence v1, no redo v1. Stack-based, in-memory, linear. Does that match the use case?

<!-- turn:2 agent:Critic -->

## Critic (skeptic)

The 100-cap will bite users on long editing sessions. Real users edit for hours. Capping silently means they hit the limit and the oldest undo just... vanishes? They'll think it's broken.

What happens when the user edits a large blob (e.g. paste a 10 MB image)? The `inverse_payload` for "delete this image" stores a 10 MB chunk in memory per stack frame. 100 frames * 10 MB = 1 GB resident memory. Not theoretical -- I've seen this exact bug in production at $LASTJOB.

Pushback: either we (a) cap by total memory not action count, or (b) skip large payloads from the undo stack and warn the user. (a) is more correct; (b) is what most editors actually do because (a) is hard.

Also: "no redo v1" -- users will hate this. Redo is table stakes for any text editor since 2002. If we ship undo without redo we'll get a flood of issues on day 1.

<!-- turn:3 agent:Implementer -->

## Implementer (hands-on coder)

Both points land. Concrete proposal:

```typescript
class UndoStack {
  private stack: EditorAction[] = [];
  private cursor: number = -1;  // for redo
  private readonly maxBytes = 50 * 1024 * 1024; // 50 MB total
  private currentBytes: number = 0;

  push(action: EditorAction): void {
    // Truncate redo tail
    this.stack = this.stack.slice(0, this.cursor + 1);
    this.stack.push(action);
    this.cursor = this.stack.length - 1;
    this.currentBytes += sizeof(action);
    this.evictUntilUnderCap();
  }
  undo(): EditorAction | null { /* ... */ }
  redo(): EditorAction | null { /* ... */ }
  private evictUntilUnderCap(): void { /* drop from front until <= maxBytes */ }
}
```

Effort: 1 day for implementation, 0.5 day for tests, 0.5 day for "what does the UI look like when stack is empty". Total: 2 days.

The Critic's point about persistence -- I agree, defer. Cross-session undo is a different problem (involves shape-stable serialization of `EditorAction`).

## Decision

AGREED on: 50 MB cap (not action count), redo from day 1, no persistence v1.

<!-- end:transcript -->
