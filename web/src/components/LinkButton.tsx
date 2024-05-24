import cn from "classnames";
import * as React from "react";
import { Link } from "react-router-dom";
import { type BaseProps } from "web-ui/components/ButtonBase";
import { ButtonBase } from "web-ui/juicy";

type LinkProps = React.ComponentProps<typeof Link>;

interface Props extends BaseProps, Omit<LinkProps, "aria-disabled"> {}

const LinkButton = (
  {
    children,
    className,
    fakeActive,
    fakeHover,
    leadingVisual,
    onTouchStart,
    size,
    state,
    trailingVisual,
    unstyledDisabled,
    unstyledHover,
    variant,
    ...rest
  }: Props,
  ref: React.Ref<HTMLAnchorElement>,
) => (
  <ButtonBase
    fakeActive={fakeActive}
    fakeHover={fakeHover}
    leadingVisual={leadingVisual}
    onTouchStart={onTouchStart}
    render={({ disabled, ...renderProps }) => (
      <Link
        {...renderProps}
        {...rest}
        aria-disabled={disabled}
        className={cn(renderProps.className, className)}
        ref={ref}
      />
    )}
    size={size}
    state={state}
    trailingVisual={trailingVisual}
    unstyledDisabled={unstyledDisabled}
    unstyledHover={unstyledHover}
    variant={variant}
  >
    {children}
  </ButtonBase>
);

export default React.forwardRef(LinkButton);
