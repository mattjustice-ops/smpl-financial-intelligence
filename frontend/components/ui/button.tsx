import * as React from "react";

import { cn } from "../../lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "lg" | "sm";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", type = "button", ...props }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/50 disabled:pointer-events-none disabled:opacity-50",
          variant === "default" && "bg-teal-400 text-slate-950 hover:bg-teal-300",
          variant === "outline" && "border border-white/20 bg-white/5 text-white hover:bg-white/10",
          variant === "ghost" && "text-slate-300 hover:bg-white/5 hover:text-white",
          size === "default" && "h-10 px-4 py-2 text-sm",
          size === "lg" && "h-12 px-7 text-base",
          size === "sm" && "h-9 px-3 text-sm",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
