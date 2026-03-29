import { Hero } from "@/components/primitives/Hero";
import { TextBlock } from "@/components/primitives/TextBlock";
import { Image } from "@/components/primitives/Image";
import { Video } from "@/components/primitives/Video";
import { CTA } from "@/components/primitives/CTA";
import { Form } from "@/components/primitives/Form";
import { OfferStack } from "@/components/primitives/OfferStack";
import { SocialProof } from "@/components/primitives/SocialProof";
import { Testimonial } from "@/components/primitives/Testimonial";
import { FAQ } from "@/components/primitives/FAQ";
import { DiagnosticEntry } from "@/components/primitives/DiagnosticEntry";
import { TrustBar } from "@/components/primitives/TrustBar";
import { ContentGrid } from "@/components/primitives/ContentGrid";
import type { ComponentType as ReactComponentType } from "react";

export const COMPONENT_REGISTRY: Record<string, ReactComponentType<any>> = {
  hero: Hero,
  text_block: TextBlock,
  image: Image,
  video: Video,
  cta: CTA,
  form: Form,
  offer_stack: OfferStack,
  social_proof: SocialProof,
  testimonial: Testimonial,
  faq: FAQ,
  diagnostic_entry: DiagnosticEntry,
  trust_bar: TrustBar,
  content_grid: ContentGrid,
};
