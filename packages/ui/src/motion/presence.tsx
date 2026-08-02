"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { motionDuration, motionEase } from "./tokens";

import type { ReactNode } from "react";

export interface PresenceProps {
  show: boolean;
  children: ReactNode;
  className?: string;
}

/**
 * Enter/exit presence for overlays and transient UI.
 * Answers "where did this go?" / "what changed?"
 */
export function Presence({ show, children, className }: PresenceProps) {
  const prefersReduced = useReducedMotion();

  return (
    <AnimatePresence>
      {show ? (
        prefersReduced ? (
          <div className={className}>{children}</div>
        ) : (
          <motion.div
            className={className}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionDuration.fast, ease: motionEase.standard }}
          >
            {children}
          </motion.div>
        )
      ) : null}
    </AnimatePresence>
  );
}
