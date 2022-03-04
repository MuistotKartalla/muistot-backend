import setuptools

setuptools.setup(
    name="mailer-local",
    version="0.0.1",
    author="TEST ONLY",
    author_email="TEST ONLY",
    description="TEST ONLY",
    long_description="TEST ONLY",
    long_description_content_type="text/markdown",
    url="TEST ONLY",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=["local_mailer"],
    python_requires=">=3.9",
)
