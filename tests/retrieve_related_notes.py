import re

def extract_links(note_path):
    """
    Extracts all wiki-style links (e.g. [[Note Title]]) from an Obsidian note.
    
    It cleans each link by removing any alias (after a '|') and any section specifier (after a '#').
    
    Args:
        note_path (str): The path to the Obsidian note file.
        
    Returns:
        set: A set of cleaned note titles mentioned in the note.
    """
    try:
        with open(note_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    # Use a regex to find all occurrences of [[...]]
    raw_links = re.findall(r'\[\[([^\]]+)\]\]', content)
    
    # Clean the links by removing aliases and section specifiers
    cleaned_links = set()
    for link in raw_links:
        main_link = link.split('|')[0].strip()  # Remove alias if present
        main_link = main_link.split('#')[0].strip()  # Remove section specifier if present
        if main_link:
            cleaned_links.add(main_link)
    
    return cleaned_links

if __name__ == '__main__':
    note_path = input("Enter the path to your Obsidian note: ").strip()
    links = extract_links(note_path)
    
    if links is None:
        print("No links were extracted due to an error.")
    else:
        print("\nRelated notes found in the Obsidian note:")
        for note in sorted(links):
            print(note)
