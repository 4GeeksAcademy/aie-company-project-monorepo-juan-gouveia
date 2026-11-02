import BrasaPoints from "@/components/BrasaPoints";
import Contact from "@/components/Contact";
import Features from "@/components/Features";
import Hero from "@/components/Hero";
import History from "@/components/History";
import JsonLd from "@/components/JsonLd";
import Locations from "@/components/Locations";
import SiteFooter from "@/components/SiteFooter";
import SiteHeader from "@/components/SiteHeader";

export default function Home() {
  return (
    <>
      <JsonLd pageName="Brasaland: El sabor de la brasa, en cada bocado" />
      <SiteHeader />
      <main>
        <Hero />
        <History />
        <Features />
        <Locations />
        <BrasaPoints />
        <Contact />
      </main>
      <SiteFooter />
    </>
  );
}
