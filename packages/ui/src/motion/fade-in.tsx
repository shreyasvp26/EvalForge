"use client";

import { motion, useReducedMotion } from "framer-motion";

import { motionDuration, motionEase } from "./tokens";

import type { HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";

export type FadeInProps = HTMLMotionProps<"div"> & {
  children: ReactNode;
  /** Skip animation when reduced motion is preferred (default true). */
  respectReducedMotion?: boolean;
};

/**
 * Subtle opacity/translate entrance. Answers "where did this come from?"
 * Prefer CSS for hover/focus; use this for mount presence only.
 */
export function FadeIn({
  children,
  className,
  respectReducedMotion = true,
  ...props
}: FadeInProps) {
  const prefersReduced = useReducedMotion();
  const disable = respectReducedMotion && prefersReduced;

  if (disable) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: motionDuration.normal, ease: motionEase.standard }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
