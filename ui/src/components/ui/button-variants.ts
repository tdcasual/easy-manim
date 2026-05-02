import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors transition-transform transition-shadow disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:-translate-y-0.5 active:scale-[0.98]",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm hover:-translate-y-0.5 active:scale-[0.98]",
        outline:
          "border border-border bg-card hover:bg-muted hover:text-foreground shadow-sm hover:-translate-y-0.5 active:scale-[0.98]",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/90 shadow-sm hover:-translate-y-0.5 active:scale-[0.98]",
        ghost: "hover:bg-muted hover:text-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        pink: "bg-pink-500 text-white hover:bg-pink-600 shadow-sm shadow-pink-500/20 hover:-translate-y-0.5 active:scale-[0.98]",
        mint: "bg-mint-500 text-white hover:bg-mint-600 shadow-sm shadow-mint-500/20 hover:-translate-y-0.5 active:scale-[0.98]",
        sky: "bg-sky-500 text-white hover:bg-sky-600 shadow-sm shadow-sky-500/20 hover:-translate-y-0.5 active:scale-[0.98]",
        lavender:
          "bg-lavender-500 text-white hover:bg-lavender-600 shadow-sm shadow-lavender-500/20 hover:-translate-y-0.5 active:scale-[0.98]",
        peach:
          "bg-peach-500 text-white hover:bg-peach-600 shadow-sm shadow-peach-500/20 hover:-translate-y-0.5 active:scale-[0.98]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-12 rounded-xl px-6 text-base",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8 rounded-lg",
        "icon-lg": "h-12 w-12 rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}
