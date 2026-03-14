"""CLI chat interface for Knowly."""

from dotenv import load_dotenv

load_dotenv()

from rag import answer


def main() -> None:
    print("\n🎓 Knowly — Chateá con tus clases")
    print("Escribí tu pregunta (o 'salir' para terminar)\n")

    while True:
        try:
            query = input("Vos: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if not query:
            continue
        if query.lower() in ("salir", "exit", "quit"):
            print("¡Hasta luego!")
            break

        try:
            resp = answer(query)
            print(f"\nKnowly: {resp}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
