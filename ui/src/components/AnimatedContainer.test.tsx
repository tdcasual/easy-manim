import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AnimatedContainer } from "./AnimatedContainer";

type ObserverEntry = {
  isIntersecting: boolean;
  target: Element;
};

class MockIntersectionObserver {
  static instances: MockIntersectionObserver[] = [];

  readonly callback: (entries: ObserverEntry[]) => void;

  constructor(callback: (entries: ObserverEntry[]) => void) {
    this.callback = callback;
    MockIntersectionObserver.instances.push(this);
  }

  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();

  trigger(target: Element, isIntersecting: boolean) {
    this.callback([{ isIntersecting, target }]);
  }
}

beforeEach(() => {
  MockIntersectionObserver.instances = [];
  vi.useFakeTimers();
  vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("in-view animated containers stay hidden until they intersect", () => {
  render(
    <AnimatedContainer animation="slide-up" trigger="in-view">
      <div>Video card</div>
    </AnimatedContainer>
  );

  const wrapper = screen.getByText("Video card").parentElement;
  expect(wrapper).not.toBeNull();
  expect(wrapper).not.toHaveClass("visible");

  act(() => {
    MockIntersectionObserver.instances[0].trigger(wrapper as Element, true);
    vi.runAllTimers();
  });

  expect(wrapper).toHaveClass("visible");
});
